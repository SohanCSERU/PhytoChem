import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.conf import settings

import os
from main.models import Compound, Plant
from core.utils.QueryHandler import query_to_df, df_to_sdf, update_sdf


def index(request):
    return render(request, 'main/index.html')


def members(request):
    return render(request, 'main/members.html')


def about(request):
    context = {
        'n_compounds': Compound.objects.all().count(),
        'n_plants': Plant.objects.all().count()
    }
    return render(request, 'main/about.html', context=context)


def results(request):
    search = request.GET['search']
    if len(search) != 0:
        if search.isnumeric():
            search = 'Phytochem_' + search.zfill(6)
        elif search[0] == 'P' and search[1:].isnumeric():
            search = 'Phytochem_' + search[1:].zfill(6)
        compounds = Compound.objects.filter(
            Q(PID=search) | Q(Smiles=search) | Q(Molecular_Formula=search) | Q(plants__name__iexact=search)).distinct()
        context = {'compounds': compounds}
        return render(request, 'main/results.html', context=context)
    return redirect('/')


def plant(request, id):
    plant = get_object_or_404(Plant, id=id)
    compounds = plant.compound_set.all()
    context = {
        'plant': plant,
        'compounds': compounds
    }
    return render(request, 'main/plant.html', context=context)


def compound(request, id):
    compound = get_object_or_404(Compound,id=id)
    lipinski = (compound.H_Bond_Donors > 5) + (compound.H_Bond_Acceptors > 10) + \
               (compound.Molecular_Weight >= 500) + (compound.logP > 5)
    plants = compound.plants.all()
    violation_color = [ '#2ECC71', '#ABEBC6', '#FADBD8', '#E74C3C', '#B03A2E']
    context = {
        'compound': compound,
        'plants': plants,
        'lipinski': lipinski,
        'violation_color': violation_color
    }
    return render(request, 'main/compound.html', context=context)


# view for download a query results
def download_file(request, search):
    # make search term as is in the PID column of database
    if search.isnumeric():
        search = 'Phytochem_' + search.zfill(6)
    # temporary path for storing download files
    temppath = os.path.join(settings.MEDIA_ROOT, 'tempDownloadFiles/')

    if os.path.isdir(temppath):
        oldfiles = os.listdir(temppath)
        for file in oldfiles:
            try:
                os.remove(temppath + file)
            except FileNotFoundError:
                pass
    else:
        os.makedirs(temppath, exist_ok=True)

    # search in the database columns PID, Smiles and
    # Molecular_Formula
    compounds = Compound.objects.filter(
        Q(PID=search) | Q(Smiles=search) | Q(Molecular_Formula=search) | Q(plants__name__iexact=search))
    compounds_df = query_to_df(compounds)
    dw_file = os.path.join(temppath, search + '.sdf')
    df_to_sdf(compounds_df, dw_file)
    return prepare_download(dw_file)


@login_required
# View for downloading all file
def download_all_file(request):
    user_email = request.user.email
    tld = re.search("@\w+\.([\w]+)([\.\w]*)", user_email).group(1)
    name = 'all_data.sdf'
    file_path = os.path.join(settings.MEDIA_ROOT, name)
    if tld == 'ac' or tld == 'edu':
        return prepare_download(file_path)
    else:
        messages.warning(request, 'You must login with your institutional mail to download the dataset')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


# not view
def prepare_download(path):
    if not os.path.exists(path):
        update_sdf()
    if os.path.exists(path):
        with open(path, 'rb') as fh:
            response = HttpResponse(fh.read(), content_type='application/octet-stream')
            response['Content-Disposition'] = 'inline; filename=' + os.path.basename(path)
            return response
    raise Http404

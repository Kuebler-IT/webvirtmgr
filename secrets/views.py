# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render, redirect

from servers.models import Compute
from secrets.forms import AddSecret
from vrtManager.secrets import wvmSecrets
from libvirt import libvirtError

def secrets(request, host_id):
    if not request.user.is_authenticated():
        return redirect('login')

    errors = []
    secrets_all = []
    compute = Compute.objects.get(id=host_id)

    try:
        conn = wvmSecrets(compute.hostname,
                          compute.login,
                          compute.password,
                          compute.type)
        secrets = conn.get_secrets()
        for uuid in secrets:
            secrt = conn.get_secret(uuid)
            try:
                secret_value = conn.get_secret_value(uuid)
            except:
                secret_value = ''
            secrets_all.append({'usage': secrt.usageID(),
                                'uuid': secrt.UUIDString(),
                                'usageType': secrt.usageType(),
                                'value': secret_value
                                })
        if request.method == 'POST':
            if 'create' in request.POST:
                form = AddSecret(request.POST)
                if form.is_valid():
                    data = form.cleaned_data
                    conn.create_secret(data['ephemeral'], data['private'], data['usage_type'], data['data'])
                    return redirect(request.get_full_path())
            if 'delete' in request.POST:
                uuid = request.POST.get('uuid', '')
                conn.delete_secret(uuid)
                return redirect(request.get_full_path())
            if 'set_value' in request.POST:
                uuid = request.POST.get('uuid', '')
                value = request.POST.get('value', '')
                conn.set_secret_value(uuid, value)
                return redirect(request.get_full_path())
    except libvirtError as err:
        errors.append(err)

    return render(request, 'secrets.html', locals())

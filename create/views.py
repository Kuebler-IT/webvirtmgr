# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render, redirect
from django.utils.translation import ugettext_lazy as _

from servers.models import Compute
from create.models import Flavor
from instance.models import Instance

from libvirt import libvirtError

from vrtManager.create import wvmCreate
from vrtManager import util
from create.forms import FlavorAddForm, NewVMForm


def create(request, host_id):
    if not request.user.is_authenticated():
        return redirect('login')

    conn = None
    errors = []
    storages = []
    networks = []
    meta_prealloc = False
    compute = Compute.objects.get(id=host_id)
    flavors = Flavor.objects.filter().order_by('id')

    try:
        conn = wvmCreate(compute.hostname,
                         compute.login,
                         compute.password,
                         compute.type)

        storages = sorted(conn.get_storages())
        networks = sorted(conn.get_networks())
        instances = conn.get_instances()
        get_images = sorted(conn.get_storages_images())
        cache_modes = sorted(conn.get_cache_modes().items())
        mac_auto = util.randomMAC()
    except libvirtError as err:
        errors.append(err)

    if conn:
        if not storages:
            msg = _("You haven't defined have any storage pools")
            errors.append(msg)
        if not networks:
            msg = _("You haven't defined have any network pools")
            errors.append(msg)

        if request.method == 'POST':
            if 'create_flavor' in request.POST:
                form = FlavorAddForm(request.POST)
                if form.is_valid():
                    data = form.cleaned_data
                    create_flavor = Flavor(label=data['label'],
                                           vcpu=data['vcpu'],
                                           memory=data['memory'],
                                           disk=data['disk'])
                    create_flavor.save()
                    return redirect(request.get_full_path())
            if 'delete_flavor' in request.POST:
                flavor_id = request.POST.get('flavor', '')
                delete_flavor = Flavor.objects.get(id=flavor_id)
                delete_flavor.delete()
                return redirect(request.get_full_path())
            if 'create_xml' in request.POST:
                xml = request.POST.get('from_xml', '')
                try:
                    name = util.get_xml_path(xml, '/domain/name')
                except util.libxml2.parserError:
                    name = None
                if name in instances:
                    msg = _("A virtual machine with this name already exists")
                    errors.append(msg)
                else:
                    try:
                        conn._defineXML(xml)
                        return redirect('instance', args=[host_id, name])
                    except libvirtError as err:
                        errors.append(err.message)
            if 'create' in request.POST:
                volumes = {}
                form = NewVMForm(request.POST)
                if form.is_valid():
                    data = form.cleaned_data
                    if data['meta_prealloc']:
                        meta_prealloc = True
                    if instances:
                        if data['name'] in instances:
                            msg = _("A virtual machine with this name already exists")
                            errors.append(msg)
                    if not errors:
                        if data['hdd_size']:
                            if not data['mac']:
                                msg = _("No Virtual Machine MAC has been entered")
                                errors.append(msg)
                            else:
                                try:
                                    path = conn.create_volume(data['storage'], data['name'], data['hdd_size'],
                                                              metadata=meta_prealloc)
                                    volumes[path] = conn.get_volume_type(path)
                                except libvirtError as msg_error:
                                    errors.append(msg_error.message)
                        elif data['template']:
                            templ_path = conn.get_volume_path(data['template'])
                            clone_path = conn.clone_from_template(data['name'], templ_path, metadata=meta_prealloc)
                            volumes[clone_path] = conn.get_volume_type(clone_path)
                        else:
                            if not data['images']:
                                msg = _("First you need to create or select an image")
                                errors.append(msg)
                            else:
                                for vol in data['images'].split(','):
                                    try:
                                        path = conn.get_volume_path(vol)
                                        volumes[path] = conn.get_volume_type(path)
                                    except libvirtError as msg_error:
                                        errors.append(msg_error.message)
                        if data['cache_mode'] not in conn.get_cache_modes():
                            msg = _("Invalid cache mode")
                            errors.append(msg)
                        if not errors:
                            uuid = util.randomUUID()
                            try:
                                conn.create_instance(data['name'], data['memory'], data['vcpu'], data['host_model'],
                                                     uuid, volumes, data['cache_mode'], data['networks'], data['virtio'],
                                                     data['mac'])
                                create_instance = Instance(compute_id=host_id, name=data['name'], uuid=uuid)
                                create_instance.save()
                                return redirect('instance', args=[host_id, data['name']])
                            except libvirtError as err:
                                if data['hdd_size']:
                                    conn.delete_volume(volumes.keys()[0])
                                errors.append(err)
        conn.close()

    return render(request, 'create.html', locals())

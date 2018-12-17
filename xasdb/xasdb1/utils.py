import json
import xdifile
import xraylib as xrl
import numpy as np
from datetime import datetime, timezone
from .models import XASFile, XASMode
import os.path

OPTIONAL_KWARGS = ( \
        ('sample', 'name'), \
        ('sample', 'prep'), \
        ('beamline', 'name'), \
        ('facility', 'name'), \
        ('mono', 'name'), \
        ('mono', 'd_spacing'), \
    )

def process_xdi_file(temp_xdi_file, request):
    value = request.FILES['upload_file']
    xdi_file = xdifile.XDIFile(filename=temp_xdi_file)
    value.seek(0)
    element = xdi_file.element.decode('utf-8')
    edge = xdi_file.edge.decode('utf-8')
    for pair in XASFile.EDGE_CHOICES:
        if edge == pair[1]:
            edge = pair[0]
            break
    kwargs = dict()
    for kwarg in OPTIONAL_KWARGS:
        try:
            kwargs['_'.join(kwarg)] = xdi_file.attrs[kwarg[0]][kwarg[1]]
        except KeyError:
            pass

    try:
        kwargs['scan_start_time'] = isotime2datetime(xdi_file.attrs['scan']['start_time'])
    except KeyError:
        pass

    if 'sample_name' not in kwargs:
        kwargs['sample_name'] = os.path.splitext(value.name)[0]

    try:
        modes = []
        arrays = {'energy': xdi_file.energy}

        if hasattr(xdi_file, 'xmu'):
            arrays['xmu'] = xdi_file.xmu
            modes.append(XASMode.XMU)

        if hasattr(xdi_file, 'i0'):
            arrays['i0'] = xdi_file.i0

        if hasattr(xdi_file, 'itrans'):
            arrays['itrans'] = xdi_file.itrans
            modes.append(XASMode.TRANSMISSION)
        elif hasattr(xdi_file, 'i1'):
            arrays['itrans'] = xdi_file.i1
            modes.append(XASMode.TRANSMISSION)

        if hasattr(xdi_file, 'ifluor'):
            arrays['ifluor'] = xdi_file.ifluor
            modes.append(XASMode.FLUORESCENCE)

        elif hasattr(xdi_file, 'ifl'):
            arrays['ifluor'] = xdi_file.ifl
            modes.append(XASMode.FLUORESCENCE)

        # special case: mutrans given,
        # itrans not available,
        # and maybe i0 not available
        if (hasattr(xdi_file, 'mutrans') and
            not hasattr(xdi_file, 'itrans')):
            if not hasattr(xdi_file, 'i0'):
                arrays['i0'] = np.ones(len(xdi_file.mutrans))
                arrays['itrans'] = np.exp(-xdi_file.mutrans)
            modes.append(XASMode.TRANSMISSION)

        if (hasattr(xdi_file, 'mufluor') and
            not hasattr(xdi_file, 'ifluor')):
            if not hasattr(xdi_file, 'i0'):
                arrays['i0'] = np.ones(len(xdi_file.mufluor))
                arrays['ifluor'] = xdi_file.mufluor
            modes.append(XASMode.FLUORESCENCE)

        if (hasattr(xdi_file, 'munorm')):
            arrays['i0'] = np.ones(len(xdi_file.munorm))
            arrays['ifluor'] = xdi_file.munorm
            modes.append(XASMode.FLUORESCENCE_UNITSTEP)

        refer_used = False
        if hasattr(xdi_file, 'irefer'):
            refer_used = True
            arrays['irefer'] = xdi_file.irefer
        elif hasattr(xdi_file, 'i2'):
            refer_used = True
            arrays['irefer'] = xdi_file.i2

        xas_file = XASFile(upload_file=value, upload_file_doi=request.POST['upload_file_doi'], uploader=request.user, element=element, edge=edge, refer_used=refer_used, **kwargs)
        xas_file.save()

        for mode in set(modes):
            xas_file.xasmode_set.create(mode=mode)

        # add arrays
        for name, array in arrays.items():
            xas_file.xasarray_set.create(name=name, array=json.dumps(array.tolist()))
        return xas_file
    except Exception:
        raise


def isotime2datetime(isotime):
    sdate, stime = isotime.split('T')
    syear, smon, sday = [int(x) for x in sdate.split('-')]
    sfrac = '0'
    if '.' in stime:
        stime, sfrac = stime.split('.')
    shour, smin, ssec  = [int(x) for x in stime.split(':')]
    susec = int(1e6*float('.%s' % sfrac))

    return datetime(syear, smon, sday, shour, smin, ssec, susec, timezone.utc)

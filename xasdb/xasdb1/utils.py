import json
import xdifile
import xraylib as xrl
import numpy as np
from .models import XASFile, XASMode

OPTIONAL_KWARGS = ( \
        ('sample', 'name'), \
        ('beamline', 'name'), \
        ('facility', 'name'), \
    )

def process_xdi_file(temp_xdi_file, request):
    value = request.FILES['upload_file']
    xdi_file = xdifile.XDIFile(filename=temp_xdi_file)
    value.seek(0)
    element = xdi_file.element.decode('utf-8')
    atomic_number = xrl.SymbolToAtomicNumber(element)
    edge = xdi_file.edge.decode('utf-8')
    kwargs = dict()
    for kwarg in OPTIONAL_KWARGS:
        try:
            kwargs['_'.join(kwarg)] = xdi_file.attrs[kwarg[0]][kwarg[1]]
        except KeyError:
            pass

    try:
        modes = []
        arrays = {'energy': xdi_file.energy}

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

        xas_file = XASFile(atomic_number=atomic_number, upload_file=value, uploader=request.user, element=element, edge=edge, refer_used=refer_used, **kwargs)
        xas_file.save()

        for mode in set(modes):
            xas_file.xasmode_set.create(mode=mode)

        # add arrays
        for name, array in arrays.items():
            xas_file.xasarray_set.create(name=name, array=json.dumps(array.tolist()))

    except Exception:
        raise

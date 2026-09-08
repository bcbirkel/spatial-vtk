Optional PhaseNet integration
=============================

Arrival picking is optional. Base metrics, spatial statistics, and the public
tutorial do not install or need PhaseNet, PyTorch, CUDA, or TensorFlow.
Existing arrival catalogs can be loaded explicitly with ``picker='catalog'``.
No fallback picker is selected when PhaseNet is unavailable.

The adapter supports the external TensorFlow implementation in
`AI4EPS/PhaseNet <https://github.com/AI4EPS/PhaseNet>`__, inspected at commit
``62005c6195638f88d077f8870ea895971062715a``. Follow that project's environment
instructions in a separate environment. Its bundled pretrained model is
``model/190703-214543``. Configure absolute paths, for example:

.. code-block:: bash

   export SVTK_PHASENET_COMMAND='/path/to/phasenet-env/bin/python /path/to/PhaseNet/phasenet/predict.py'

Pass ``model_dir='/path/to/PhaseNet/model/190703-214543'`` to
``build_phasenet_arrival_pick_catalog``. The command must run from any working
directory. Shell expressions are not supported; use an executable wrapper if
you need environment setup.

The adapter writes a ``fname`` CSV and NPZ files with float32 ``data`` of shape
(samples, 3), ``station_id``, and ``t0``. Use aligned broadband E/N/Z components
at 100 Hz for the pretrained model. Resample explicitly before calling it;
filtering to the tutorial 1 Hz passband is inappropriate for arrival picking.
The legacy R/T/Z input convention is retained, but its scientific suitability
for this pretrained model has not been validated.

The command must accept ``--data_dir``, ``--data_list``, ``--format numpy``,
``--result_dir``, ``--result_fname``, ``--model_dir``, ``--sampling_rate``,
``--min_p_prob`` and ``--min_s_prob``. The output CSV must contain
``file_name``, ``phase_type``, ``phase_score``, and ``phase_time`` or
``phase_index``. Sample indices are divided by the sampling rate, then shifted
from waveform start to the supplied event origin. The highest-probability pick
per phase and input is retained. Unknown filenames and incompatible schemas
raise errors.

The separately inspected PyPI ``phasenet==0.2.5`` installs
``phasenet-predict = predict:cli``. It is a PyTorch implementation using
``--data_path``/``--result_path`` and defaults to DAS, HDF5, and CUDA. Its
checkpoint loading and formats differ from this adapter. Installing that
package or renaming its executable does not provide the supported backend.
Contract tests cover this boundary; full external model inference is a
separate validation requirement, not established by the package test suite.

During the repair audit, a clean Python 3.12 installation of PyPI PhaseNet 0.2.5
with its dependencies failed even at ``phasenet-predict --help``: its installed
``predict.py`` imports ``SeismicNetworkIterableDataset``, which its
``phasenet.data`` package does not export. This is an upstream package defect.
The external TensorFlow backend's pinned ``tensorflow==2.11.0`` environment is
not available for the local Python 3.12 interpreter, so pretrained model
inference has not been validated in this repair. The subprocess contract test
uses a labeled test executable and is not evidence of neural inference.

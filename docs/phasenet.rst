Use PhaseNet arrival picks (optional)
=====================================

The base spatial-vtk package does not require PhaseNet. PhaseNet is not included
in the package prerequisites or installed with spatial-vtk because it requires
a separate machine-learning environment and substantial dependencies. You can
calculate metrics, run waveform quality control (QC), and follow the tutorials
without installing it.

Use PhaseNet if you want to identify P- and S-wave arrivals automatically.
You can run it through spatial-vtk or import picks from a separate PhaseNet run.
If you already have picks, skip to `Use existing PhaseNet outputs`_.

.. contents:: On this page
   :local:
   :depth: 1

Install PhaseNet
----------------

The spatial-vtk integration uses the TensorFlow implementation from
`AI4EPS/PhaseNet <https://github.com/AI4EPS/PhaseNet>`_. Install it in a separate
Conda environment so its dependencies do not affect your spatial-vtk environment.
The package named ``phasenet`` on PyPI uses a different interface; installing it
with ``pip install phasenet`` does not set up this integration.

1. Install `Miniconda <https://docs.conda.io/projects/miniconda/en/latest/>`_
   and Git if they are not already available.

2. In a terminal, download PhaseNet and open its directory:

   .. code-block:: bash

      git clone https://github.com/AI4EPS/PhaseNet.git
      cd PhaseNet

3. Create and activate the PhaseNet environment:

   .. code-block:: bash

      conda env create -f env.yaml
      conda activate phasenet

   On a Mac with Apple silicon, use ``env_mac.yaml`` instead of ``env.yaml``.
   See the `PhaseNet installation instructions
   <https://github.com/AI4EPS/PhaseNet#1-install-miniconda-and-requirements>`_
   for platform-specific requirements.

4. Check that the prediction command starts, then display the paths you will
   need in spatial-vtk:

   .. code-block:: bash

      python phasenet/predict.py --help
      python -c "import sys; from pathlib import Path; print(sys.executable); print(Path('phasenet/predict.py').resolve()); print(Path('model/190703-214543').resolve())"

   The three paths identify the Python interpreter, prediction script, and
   bundled pretrained model. If the help command fails, resolve the PhaseNet
   installation problem before continuing.

Connect PhaseNet to spatial-vtk
-------------------------------

1. Return to your spatial-vtk environment. Install waveform support there if
   you have not already done so:

   .. code-block:: bash

      python -m pip install "spatial-vtk[waveforms]"

2. In your Python script or notebook, set the three absolute paths from the
   installation step. Replace the example paths with your own:

   .. code-block:: python

      import shlex

      phasenet_python = "/absolute/path/to/phasenet-env/bin/python"
      phasenet_script = "/absolute/path/to/PhaseNet/phasenet/predict.py"
      model_dir = "/absolute/path/to/PhaseNet/model/190703-214543"
      phasenet_command = shlex.join([phasenet_python, phasenet_script])

   spatial-vtk runs this command in the separate PhaseNet environment. You do
   not need to install TensorFlow in your spatial-vtk environment.

3. Prepare one waveform group per event, station, and waveform source. Use
   broadband east, north, and vertical (E/N/Z) traces at 100 Hz with matching
   start times and lengths. Align and resample your traces before this step.
   Run picking before rotating to R/T/Z or applying the metric passbands or
   the 1 Hz spectral lowpass.

   The example below uses a three-component MiniSEED file. Replace its path,
   identifiers, and event origin with those for your data:

   .. code-block:: python

      from obspy import read

      stream = read("data/event_001_station_ABC.mseed")
      groups = [{
          "event_id": "event_001",
          "station": "ABC",
          "waveform_source": "observed",
          "relative_time_origin": "2026-01-01T00:00:00Z",
          "components": {
              component: stream.select(component=component)[0]
              for component in ("E", "N", "Z")
          },
      }]

   Use event and station identifiers that match your event-station records.
   Set ``waveform_source`` to ``observed`` or ``synthetic`` as appropriate.
   Always supply the event origin: QC uses pick times measured in seconds
   since that origin, which may differ from the waveform start time.

4. Run PhaseNet and save the arrival catalog:

   .. code-block:: python

      from spatial_vtk.metrics.calculate import build_phasenet_arrival_pick_catalog

      catalog_path = build_phasenet_arrival_pick_catalog(
          groups,
          phasenet_command=phasenet_command,
          model_dir=model_dir,
          work_dir="outputs/phasenet",
          output_catalog="outputs/arrival_picks.csv",
          min_p_prob=0.5,
          min_s_prob=0.5,
      )

   The function prepares the input files, runs PhaseNet, and keeps the
   highest-probability pick for each phase and waveform group. The probability
   thresholds shown here are examples; choose them for your dataset and review
   the resulting picks. Use ``overwrite=True`` when deliberately replacing an
   existing catalog and its prepared inputs.

Use the picks in waveform QC
----------------------------

Arrival picking is a preparation step before waveform QC. Pass the saved
catalog to your existing QC call:

.. code-block:: python

   from spatial_vtk.qc.build.workflow import build_waveform_qc_summary

   qc = build_waveform_qc_summary(
       event_station_records,
       arrival_pick_catalog=catalog_path,
       onset_phase="P",
       min_onset_pick_probability=0.5,
   )

Here, ``event_station_records`` is the same table or file you already use for
waveform QC. Retain any source, component, preprocessing, and passband settings
from your existing call.

QC uses an accepted P pick to position its noise and signal windows. If a pick
is missing or fails the QC plausibility check, QC uses its waveform-envelope
onset estimate. You can select S picks with ``onset_phase="S"``. The catalog
contains station-level picks (``component="ALL"``), which can be used across
the station's components.

Continue with your usual QC review and metric workflow. PhaseNet does not run
automatically when you calculate PGA, PGV, PGD, PSA, or FAS, and supplying picks
does not change their filtering settings. See the :doc:`reference/api/qc` and
:doc:`reference/api/metrics` for the function parameters.

Use existing PhaseNet outputs
-----------------------------

You do not need to install or run PhaseNet in your spatial-vtk environment to
use picks generated elsewhere. Convert the output once, then pass the resulting
catalog to QC as shown above.

Convert a PhaseNet CSV
~~~~~~~~~~~~~~~~~~~~~~

1. Keep the PhaseNet CSV and a record of the event, station, waveform source,
   waveform start, sampling rate, and event origin for each input file.
   The CSV must contain ``file_name``, ``phase_type``, ``phase_score``, and
   either ``phase_time`` (an absolute timestamp) or ``phase_index`` (a sample
   index). Use one pick per row.

2. Create a metadata record for each input file. Match ``file_name`` exactly
   to its value in the PhaseNet CSV. This example describes one file; add a
   record for every file in your dataset:

   .. code-block:: python

      from spatial_vtk.metrics.calculate.phasenet_adapter import (
          PhaseNetInputRecord,
          normalize_phasenet_output,
      )
      from spatial_vtk.metrics.calculate import write_arrival_pick_catalog

      records = [PhaseNetInputRecord(
          file_name="event_001_station_ABC.mseed",
          event_id="event_001",
          station="ABC",
          waveform_source="observed",
          components=("E", "N", "Z"),
          sampling_rate=100.0,
          time_anchor="2025-12-31T23:59:50Z",
          relative_time_origin="2026-01-01T00:00:00Z",
      )]

3. Convert and save the picks:

   .. code-block:: python

      picks = normalize_phasenet_output(
          "results/picks.csv",
          records,
          min_p_prob=0.5,
          min_s_prob=0.5,
      )
      catalog_path = write_arrival_pick_catalog(
          picks, "outputs/arrival_picks.csv"
      )

   The converter calculates seconds since the event origin and retains the
   highest-probability pick per phase and input file. For sample-index outputs,
   it uses the sampling rate and waveform start time. For example, sample
   1500 at 100 Hz is 15 seconds after the waveform starts; if the waveform
   starts 10 seconds before the event, the catalog pick time is 5 seconds.

4. Pass ``catalog_path`` to ``build_waveform_qc_summary`` using the example in
   `Use the picks in waveform QC`_. This conversion and QC path does not call
   PhaseNet.

Load a catalog you have already converted
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If your workflow already produces a spatial-vtk arrival catalog, load its CSV
or Parquet file directly:

.. code-block:: python

   from spatial_vtk.metrics.calculate import load_arrival_pick_catalog

   picks = load_arrival_pick_catalog("outputs/arrival_picks.csv")

Pass ``picks`` as ``arrival_pick_catalog`` in your QC call. Use these columns
when converting another output format yourself:

.. list-table:: Arrival catalog columns
   :header-rows: 1
   :widths: 30 70

   * - Column
     - Value
   * - ``event_id``, ``station``
     - Identifiers matching your event-station records.
   * - ``component``
     - ``ALL`` for a station-level pick, or a specific component.
   * - ``phase``
     - ``P`` or ``S``.
   * - ``pick_time_abs``
     - Absolute pick timestamp, preferably in UTC.
   * - ``pick_time_rel_s``
     - Numeric seconds since the event origin; required for QC to use the pick.
   * - ``probability``
     - Numeric pick confidence used by the probability filter.
   * - ``method``
     - ``phasenet`` for PhaseNet picks.
   * - ``source``
     - ``observed`` or ``synthetic``. Include this to keep the two sources separate.

Loading a catalog does not convert raw PhaseNet columns or calculate relative
pick times. Use the converter above for those steps.

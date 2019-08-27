Running OnDA
============


.. contents::
   :local:





What Is An OnDA Monitor?
------------------------


Real-time Monitoring
^^^^^^^^^^^^^^^^^^^^

OnDA is a framework for the development of programs that can be used to monitor
experiments in real-time (or quasi-real time, depending on your definition). This kind
of programs retrieve data from a facility as soon as possible after data is collected,
and perform some fast, simple analysis on it. The goal is to provide the people running
the experiment enough information to make quick decisions.

Usually, it is not strictly necessary to process all the data being collected in order
to provide enough information for the decision making (for example, the hit rate for a
Serial Crystallography experiment can be computed with high accuracy by analyzing only
a portion of the collected data). It is however crucial that the information provided
is up to date. Because of this, OnDA always prioritizes the processing of recently
collected data over the processing of all collected data. Completeness is not the main
priority, low latency in providing the information is. Additionally, the goal of OnDA
is strictly to provide quick information to the people running the experiment, not any
long-term analysis of the data: after the information is delivered to the user, the
data is discarded without being saved to disk, and new data is retrieved from the
facility.

In order to achieve its goals of speed and high throughput in data processing, OnDA
takes advantage of a master / worker parallel architecture. Several processing units
('worker nodes' in OnDA parlance) retrieve data events (a single frame or a collection
of frames presented as a single unit by the facility) from a facility source, and
process them. A 'master' node collects information from the workers and performs
computations over multiple events (averaging, aggregation, etc.). The data is finally
presented to the users in the console or sent to external programs for visualization.

OnDA is mostly written using the Python programming language, however, some processing
routines are implemented in other languages (C, C++) for performance reasons.


The Three Layers
^^^^^^^^^^^^^^^^

In the OnDA framework, a monitoring program is split into four cleanly separate parts
(or 'Layers', in OnDA parlance):

* A part which deals with the running logic of the program (set up and finalization of
  the worker and master nodes, communication between the nodes, etc.). This is called
  'Parallelization Layer'.

* A part that deals with the retrieval of data from a facility and with the extraction
  of information from it. This is the 'Data Retrieval Layer'.

* A part that deals with the scientific processing of the extracted data. This is
  called the 'Processing Layer'.

The first two layers are usually different for each facility or beamline. The last
layer, however, encodes the logic of the scientific processing of the data. When the
same type of monitor is run at different facilities, the same code is run for the
Processing Layer. Its interface with the other layers is very clearly defined, so they
can swapped for different implementations without any change to the the Processing
Layer itself.

This clean interface is the reason why a developer who wants to write a monitoring
program does not need to worry how data is retrieved from each specific facility, or 
passed around the nodes. All he or she needs to learn is how the data can be accessed
and manipulated in the Processing Layer. No knowledge of the other two layers is
required. A monitoring program implementation written for a facility can in most
cases be run at other facilities just by switching to different implementations of the
Data Retrieval and Parallelization layers.


How To Start An OnDA Monitor
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

On a local machine, an OnDA monitor is usually started using the following command:

.. code-block:: bash

    onda_monitor.py --config CONFIGURATION_FILE SOURCE_STRING

Or, when the 'mpi' implementation of the Paralleization Layer is used:

.. code-block:: bash

    mpirun -n <NUM NODES> onda_monitor.py --config CONFIGURATION_FILE SOURCE_STRING

An OnDA monitor requires two pieces of information to operate: a source of data events,
and a set of configuration parameters. Information about the data source is usually
provided as an argument to the monitor's start up script, in the form of a 'source
string'. Configuration parameters, which fully determine the behavior of the monitor,
are instead stored in a configuration file. Both are discussed in the following
paragraphs. 




The Source String
-----------------

Information about the source of data events is provided to OnDA at start-up, in the
form of a command line argument to the 'onda_monitor.py' script.

.. code-block:: bash

    onda_monitor.py SOURCE_STRING

It usually consists of a string, the 'Source String', which encodes the information in
a way that depends on the specific Data Retrieval Layer implementation used by the
monitor. This information is usually provided by the developer that configured the
Data Retrieval Layer, and is often specific to the facility where the experiment is
taking place. The following is a list of the facilities currently officially supported
by OnDA, with a description of the typical format of the source string at each of
them.


Filesystem
^^^^^^^^^^

When the source of data for the monitor is the filesystem, the source string is the
relative or absolute path to a file containing a list of files that the monitor must
process. The files that must be process must be listed one per line, each with their
full relative or absolute path. Example: files.lst


LCLS
^^^^

When OnDA runs at the LCLS facility, the source string is a psana-style DataSource
string. Example: shmem=psana.0:stop=no


Petra III
^^^^^^^^^

When the monitor runs at the Petra III facility, the source string is the ip or
the hostname of the machine where HiDRA is running. Example: eval01.desy.de





The Configuration File
----------------------

The behaviour of an OnDA monitor is completely determined by the content of its
configuration file. By default, OnDA looks for a file called 'monitor.toml' in the
current working directory. However, the '--config' command line option to the
'onda_monitor.py' script allows a custom location for the configuration file to be
specified.

.. code-block:: bash

    onda_monitor.py --config PATH_TO_CONFIG_FILE SOURCE_STRING

The content of the configuration file must formatted according to the rules of the 
`TOML <https://github.com/toml-lang/toml>`_ language. This language is not very
different from the one traditionally used by Python 'ini' files. The main differences
are:

* Strings (including file and directory paths) must be always enclosed within single or
  double quotes (' or ").

* The 'True' and 'False' keywords are spelled without a capital first letter ('true'
  and 'false' respectively)

* There is no 'None' value. To set a parameter value to 'None', the parameter must
  be commented out or completely omitted from the configuration file.

The parameters in the configuration file are divided into groups ('Tables' in TOML
parlance). Each group contains a set of parameters that are related to each other
(for example, because they apply to the same OnDA algorithm, or because they control
the same feature of the monitor).

.. code-block:: ini

    [General]
    broadcast_ip = '127.0.0.1'
    broadcast_port = 12321
    speed_report_interval = 1000

The following is an alphabetical list of the parameter groups that can be found in the
configuration file. Depending on which OnDA monitor is being run, not all the groups
need to be present in the file at the same time. Conversely, custom OnDA monitors might
introduce additional groups not described here. For each group, a list of the available
parameters is provided. While some parameter are strictly required (again depending on
the type of OnDA monitor), others are optional. If a parameter that is not strictly
required is not found in the configuration file, its default value is considered to be
'None'.

.. warning::
   When a parameter is a physical constant, it is assumed to be expressed in SI units
   unless the parameter name says otherwise!!


[Correction]
^^^^^^^^^^^^

This parameter group contains information used by OnDA for the correction of detector
frames (using the :class:`Correction 
<onda.algorithms.generic_algorithms.Correction>` algorithm).

* **dark_filename (str or None):** the relative or absolute path to an HDF5 file
  containing a dark data frame. Defaults to None. If this and the ‘dark_hdf5_path’
  arguments are not None, the dark data is loaded applied to the detector frame.
  Example: 'run21_dark.h5'

* **dark_hdf5_path (str or None):** the internal HDF5 path to the data block where the
  dark data frame is located. If the ‘dark_filename’ argument is not None, this
  argument must also be provided, and cannot be None. Otherwise it is ignored. Example:
  '/data/data'

* **gain_filename (str or None):** the relative or absolute path to an HDF5 file
  containing a gain map. If this and the ‘gain_hdf5_path’ arguments are not None, the
  gain map is loaded applied to the detector frame. Each pixel in the gain map must
  store the gain factor that will be applied to the corresponing pixel in the detector
  frame. Example: 'cspad_gain_map.h5'

* **gain_hdf5_path (str or None)** the internal HDF5 path to the data block where the
  gain map data is located. If the ‘gain_filename’ argument is not None, this argument
  must also be provided, and cannot be None. Otherwise it is ignored. Example:
  '/data/data'

* **mask_filename (str or None):** the relative or absolute path to an HDF5 file
  containing a mask. If this and the ‘mask_hdf5_path’ arguments are not None, the mask
  is loaded applied to the detector frame. The pixels in the mask must have a value of
  either 0, meaning that the corresponfing pixel in the detector frame must be set to
  0, or 1, meaning that the value of the corresponding pixel must be left alone.
  Example: 'run18_mask.h5'

* **mask_hdf5_path (str or None):** the internal HDF5 path to the data block where the
  mask data is located. If the ‘mask_filename’ argument is not None, this argument must
  also be provided, and cannot be None. Otherwise it is ignored. Example: '/data/data'


[Crystallography]
^^^^^^^^^^^^^^^^^

This group contains parameters used by the OnDA monitor for crystallography.

* **geometry_file (str):** the absolute or relative path to a geometry file in
  `CrystFEL <http://www.desy.de/~twhite/crystfel/manual-crystfel_geometry.html>`_
  format. Example: 'pilatus.geom'.

* **geometry_is_optimized (bool):** whether the geometry is optimized. This information
  is broadcasted by the monitor and used by external programs. For example, the OnDA
  GUI for crystallography uses this information to decide if the drawing of
  resolution rings should be allowed or not (if the geometry is not optimized, the
  rings are not reliable). Example: false.

* **hit_frame_sending_interval (int or None):** this parameter determines how often the
  monitor sends *full detector frames* to external programs (as opposed to reduced
  data). It applies only to frames labelled as hits. If the value of this parameter is
  None, no hit frames are ever sent. If the value is a number, it is the number of hit
  frames that *each worker* skips before sending the next frame to the master node to
  be broadcasted. If, for example, the value of this parameter is 5, each worker sends
  every 5th hit frame to the master for broadcasting. Example: 10

* **max_num_peaks_for_hit (int):** the maximum number of Bragg peaks that can be found
  in a detector frame for the frame to be labelled as a hit. Example: 500.

* **max_saturated_peaks (int):** the maximum number of saturated Bragg peaks that can
  be found in a detector before the frame itself is labelled as saturated. A saturated
  Bragg peak is a peak whose integrated intensity (in ADUs) goes beyond the value
  specified by the 'saturation_value' parameter in this same group.

* **min_num_peaks_for_hit (int):** the minimum number of Bragg peaks that need to be
  found in a detector frame for the frame to be labelled as a hit. Example: 10

* **non_hit_frame_sending_interval (int or None):** this parameter determines how often
  the monitor sends *full detector frames* to external programs (as opposed to reduced
  data). It applies only to frames that have not been labelled as hits. If the value of
  this parameter is None, no non-hit frames are ever sent. If value is a number, it is
  the number of non-hit frames that *each worker* skips before sending the next frame
  to the master node to be broadcasted. If, for example, the value of this parameter is
  100, each worker sends every 100th non-hit frame to the master for broadcasting.
  Example: 1000

* **running_average_window_size (int):** the size of the running window used by the
  monitor to compute the average hit and saturation rates. The rates are computed
  over the number of most recent events specified by this parameter. Example: 100.

* **saturation_value (float):** the minimum value (in ADUs) of the integrated intensity
  of a Bragg peak for the peak to be labelled as saturated. The value of this parameter
  usually depends on the specific detector being used. Example: 5000.5.


[DataAccumulator]
^^^^^^^^^^^^^^^^^

This group contains a parameter that dictates how OnDA aggregates events in the master
node before sending them to external programs. It refers to the :class:`DataAccumulator
<onda.algorithms.generic_algorithms.DataAccumulator>` algorithm.

* **num_events_to_accumulate (int):** number of events for which data is accumulated in
  the master node before being broadcasted in a single transmission.  Example: 20


[DataRetrievalLayer]
^^^^^^^^^^^^^^^^^^^^

This parameter group contains information that determines how the Data Retrieval Layer
extracts data from a facility framework.


.. warning::
   Please exercise caution when changing the parameters in this group: a wrong choice
   can severly interfere with data retrieval and extraction.


* **fallback_beam_energy_in_eV (float)** the beam energy *in eV*. OnDA uses this
  fallback value when the framework does not provide beam energy information.
  Example: 12000

* **fallback_detector_distance_in_mm (float)** the detector distance *in mm*. OnDA
  uses this fallback value when the framework does not provide detector distance
  information. Example: 250

* **hidra_base_port (int):** the base port used by the HiDRA framework to send data
  to the worker nodes. HiDRA will use this port and the following ones (one per node)
  to contact the workers. The machine where OnDA is running and the one where HiDRA is
  running should be able to reach each other at this port and the immediately following
  ones. Example: 52000

* **hidra_transfer_type ('data' or 'metadata'):** the transfer type used by the HiDRA
  framework for the current monitor. If this parameter has a value of 'data', OnDA asks
  HiDRA to stream the detector data to the monitor. If instead the value is 'metadata',
  OnDA asks HiDRA to just stream information on where in the filesystem the most recent
  data can be found. Usually it is automatically determined from the detector(s) model
  currently used by the monitor, but it can be overridden using this parameter.
  Example: 'data'

* **karabo_detector_label (str):** the label of the main x-ray detector from which 
  the Karabo framework retrieves data. Example:
  'SPB_DET_AGIPD1M-1/CAL/APPEND_CORRECTED'

* **karabo_max_event_age (float or None):** the maximum age (in seconds) that a data
  event retrieved from Karabo must have in order to be processed. If the age of the
  event, defined as the time between data collection and the retrieval of the event by
  OnDA, is higher than this threshold, the event is not processed and a new event is
  retrieved. If the value of this parameter is None, all events are processed. Example:
  0.5

* **num_of_most_recent_frames_in_event_to_process (int or None):** number of frames for
  each event to process. Please notice that this are the *most recent* events: if the
  value of this paramerer is, for example, 100, only the *last* 100 frames in the event
  are processed. If the value of this parameter is None, all events are processed.
  Example: 0.5

* **psana_detector_name (str):** * **karabo_detector_label (str):** the name of the
  main x-ray detector from which the psana framework retrieves data. Example:
  'DscCsPad'

* **psana_detector_distance_epics_name (str):** the name of the Epics device from which
  the psana framework retrieves detector distance information for the main x-ray
  detector. Example: 'CXI:DS1:MMS:06.RBV'

* **psana_digitizers_name (str):** the name of the main digitizer device from which
  the psana framework retrieves information.

* **psana_evr_source (str):** name of the EVR source from which the psana framework
  retrieves information.

* **psana_opal_name (str):** the name of the Opal camera from which the psana framework
  retrieves information.

* **psana_timetool_epics_name (str):** the name of the Epics device from which
  the psana framework retrieves timetool information.

* **psana_max_event_age (float or None):** the maximum age (in seconds) that a data
  event retrieved from psana must have in order to be processed. If the age of the
  event, defined as the time between data collection and the retrieval of the event by
  OnDA, is higher than this threshold, the event is not processed and a new event is
  retrieved. Example: 0.5




[DetectorCalibration]
^^^^^^^^^^^^^^^^^^^^^

This parameter group contains information used by OnDA for the calibration of
detector frames, using one of the calibration algorithms defined
:doc:`here <onda.algorithms.calibration_algorithms>`.

* **calibration_algorithm (str or None):** name of the calibration algorithm that the
  current monitor uses to calibrate the detector frame. The value of this parameter
  must be None or match one of the names of the calibration algorithms. If the value is
  None, no calibration will be performed. Example: 'Agipd1MCalibration'

* **calibration_filename (str or None):** absolute or relative path to an HDF5 file
  containing the calibration parameters. The exact format of this file depends on the
  calibration algorithm being used. Please consult the documentation for the specific
  algorithm. If no calibration is performed, this parameter is ignored. Example:
  'agipd_calibration_params.h5'


[General]
^^^^^^^^^

This parameter group is a generic catch-all category for parameters that don't fit in
any other group. Many of the parameters in this group are related to the way the OnDA
monitor broadcasts the data to external programs for visualization.

* **broadcast_ip (str or None):** the hostname or ip address where the monitor
  broadcasts data to external programs. If the value of this parameter is None, the ip
  is autodetected. This is usually fine. An ip or hostname must be usually manually
  specified in exceptional cases (e.g: multiple network interfaces on the same
  machine). Example: '127.0.0.1'

* **broadcast_port (int or None):** the port where the monitor broadcasts data to
  external programs. If the value of this parameter is None, port 12321 is used. 
  Example: 12322

* **speed_report_interval (int):** the number of events that must pass between
  consecutive speed reports from OnDA. This parameter determines how often OnDA prints
  the 'Processed: ..' message that provides information for about the processing speed.
  Exaple: 100


[Onda]
^^^^^^

.. DANGER::
   !! This section determines the core behavior of the OnDA monitor. Do not modify it
   unless you know what your are doing !!

* **data_retrieval_layer (str):** name of the python module with the implementation of
  the Data Retreival Layer for the current monitor. Example: 'lcls_spb'

* **paralelization_layer (str):** name of the python module with the implementation of
  the Parallelization Layer for the current monitor. Example: 'mpi'

* **processing_layer (str):** name of the python module with the implementation of the
  Processing Layer for the current monitor. Example: 'crystallography'

* **required_data (List[str]):** data that the current monitor should retrieve for
  each event. For each type of data, a corresponding Data Extraction Function must be
  defined in the Data Retrieval Layer. If this condition is met, the extracted data
  will be available in the 'data' object in the Processing layer.
  Example: ['detector_data', 'detector_distance', 'beam_energy','timestamp']




[Peakfinder8PeakDetection]
^^^^^^^^^^^^^^^^^^^^^^^^^^

This parameter group contains parameter used by the OnDA monitor to perform Bragg peak
finding on a detector frame, using the (using the :class:`Peakfinder8PeakDetection\ 
<onda.algorithms.crystallography_algorithms.Peakfinder8PeakDetection>` algorithm).

* **adc_threshold (float):** minimum ADC threshold for peak detection. Example: 200

* **bad_pixel_map_filename (str):** absolute or relative path to an HDF5 file
  containing a bad pixel map. The map is used mark areas of the data frame that must be
  excluded from the peak search. Each pixel in the map must have a value of either 0,
  meaning that the corresponding pixel in the data frame must be ignored, or 1, meaning
  that the corresponding pixel must be included in the search. The map is only used to
  exclude areas from the peak search: the data is not modified in any way. Example:
  'bad_pixel_mask.h5'
  
* **bad_pixel_map_hdf5_path (str):** internal HDF5 path to the data block where the
  a bad pixel map is stored. See the 'bad_pixel_map_filename' parameter. Example:
  '/data/data'

* **max_num_peaks (int):** maximum number of peaks that will be retrieved from each
  data frame. Additional peaks will be ignored. Example: 2048

* **local_bg_radius (int):** radius for the estimation of the local background in
  pixels. Example: 3

* **max_pixel_count (int):** maximum size of a peak in pixels. Example: 10

* **max_res (int):** maximum resolution for a peak in pixels. Example: 800

* **min_pixel_count (int):** minimum size of a peak in pixels. Example: 1

* **minimum_snr (float):** minimum signal-to-noise ratio for peak detection. Example:
  5.0

* **min_res (int):** minimum resolution for a peak in pixels. Example: 20





Errors
------

When something does not work as expected, an OnDA monitor can report an error. Errors
can be fatal, in which case the monitor simply exits, or not, and the monitor simply
reports the error and continues processing data.

OnDA errors are not reported as normal python errors. They are clearly labelled as
coming from the monitor, and their traceback information is removed. The '--debug'
options of the 'onda_monitor.py' script disables this behavior and forces OnDa to
report all errors as normal python errors.

When the mpi Parallelization layer is used, OnDA fatal errors are often reported
multiple times before the monitor stops This is normal: it can happen that multiple
nodes report the same error before the MPI engine has time to stop.

A list of the most common errors reported by OnDA follows, with a brief discussion of
each.


OndaConfigurationFileReadingError
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

There was a problem finding or reading the configuration file. Please check that the
file exists and is readable. Remember that OnDA looks by default for a file called
'monitor.toml' in the current working directory.


OndaConfigurationFileSyntaxError
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

There is a syntax error in the configuration file, where specified by the error. Make
sure that the file follows the  `TOML <https://github.com/toml-lang/toml>`_ syntax.


OndaDataExtractionError
^^^^^^^^^^^^^^^^^^^^^^^

An error has happned during the extraction of data from an event. This error is usualy
not fatal and can happen often if the data stream is corrupted. Usually OnDA skips
processing the event and retrieves a new one.


OndaHdf5FileReadingError
^^^^^^^^^^^^^^^^^^^^^^^^

An error has happened while reading an HDF5 file. Please check that the file exists and
is readable.


OndaHidraAPIError
^^^^^^^^^^^^^^^^^

An error has happened during the connection with the HiDRA framework. Check that HiDRA
is running at that the source string specifies the correct machine.


OndaInvalidSourceError
^^^^^^^^^^^^^^^^^^^^^^

The format of the source string is not valid. Check that there are no typos in the
string and that you are not using a string for a different facility.


OndaMissingDependencyError
^^^^^^^^^^^^^^^^^^^^^^^^^^

One of the optional python module needed by OnDA at some facilities is not installed.
This error often happens with python modules from facility frameworks (for example,
the psana module). Please contact one of the developers.


OndaMissingDataExtractionFunctionError
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

One of the Data Extraction Functions is not defined in the Data Retrieval Layer. Please
contact one of the developers.


OndaMissingEventHandlingFunctionError
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

One of the Event Handling Functions is not defined in the Data Retrieval Layer. Please
contact one of the developers.


OndaMissingHdf5PathError
^^^^^^^^^^^^^^^^^^^^^^^^

An internal path in the HDF5 file is not found. The file exists and can be read, but
the iternal path cannot be found. Please check that the HDF5 path is correct.


OndaMissingParameterError
^^^^^^^^^^^^^^^^^^^^^^^^^

A required parameter is missing from the configuration file.


OndaMissingParameterGroupError
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A parameter group (a section beginning with a string between square brackets - for
example, '[Onda]') is missing from the configuration file.


OndaMissingPsanaInitializationFunctionError
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

One of the psana Detector Interface Initialization Functions is not defined in the Data
Retrieval Layer. Please contact one of the developers.


OndaWrongParameterTypeError
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The type of the parameter in the configuration file does not match the requested one.
Check if the type (string, float, int) of the parameter in the configuration file is
correct. 
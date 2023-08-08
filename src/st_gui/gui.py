import streamlit as st
import os
from io import StringIO
from pathlib import Path

import time

import yaml

import wrftamer
from wrftamer import res_path
from wrftamer.wrftamer_paths import wrftamer_paths
from wrftamer.main import Project, list_projects, reassociate
from wrftamer import cfg
import wrftamer.wrftamer_functions as wtfun

# -----------------------------------------------------------------------------------------------------------------------
# Variables and Helpers
# -----------------------------------------------------------------------------------------------------------------------


home_path, db_path, run_path, archive_path, plot_path = wrftamer_paths()

# Try to read poi file from file selector
try:
    poi_file = os.environ["WRFTAMER_DEFAULT_POI_FILE"]
except KeyError:
    poi_file = None

try:
    levs_per_var_file = os.environ["WRFTAMER_DEFAULT_LEVS_PER_VAR_FILE"]
except KeyError:
    levs_per_var_file = str(res_path / 'Levels_per_variable.yaml')

list_of_projects = list_projects(verbose=False)
list_of_projects.insert(0, None)


class Fake_Project:

    @staticmethod
    def list_exp(verbose=False):
        return []


# ----------------------------------------------------------------------------------------------------------------------
# Sidebar
# ----------------------------------------------------------------------------------------------------------------------

verbose = st.sidebar.checkbox('verbose (for debugging)')
proj_name = st.sidebar.selectbox('Choose Project', options=list_of_projects)

try:

    proj = Project(proj_name)
    proj_df = proj.exp_provide_info()

    exp_name = st.sidebar.selectbox('Choose Experiment', options=proj.list_exp(verbose=False))

    setup_required = False

except FileNotFoundError:
    proj = Fake_Project()
    proj_df = None
    setup_required = True

# -----------------------------------------------------------------------------------------------------------------------

proj_tab, exp_tab, reass_tab, setup_tab = st.tabs(['Projects', 'Experiments', 'Reassociate Experiments', 'Setup'])

with proj_tab:
    if setup_required:
        st.error('Several paths WRFtamer needs haven not been defined. Got to Setup tab or run wt fist_steps.')
    else:
        col1, col2 = st.columns([0.25, 0.75])

        col2.markdown('**Experiments found for selected project**')
        col2.table(proj_df)

        col1.markdown('**Project Management**')
        new_proj_name = col1.text_input('New Project Name')

        if col1.button('Create new project', use_container_width=True):

            try:
                new_proj = Project(new_proj_name)
                new_proj.create(verbose=verbose)
                st.sidebar.success('Project successfuly created.')
                time.sleep(1)
                st.experimental_rerun()
            except FileExistsError:
                st.sidebar.error("A project with this name already exists. Remove project or choose a different name")
            except ValueError as err_msg:
                st.sidebar.error(err_msg)

        if col1.button('Rename project', use_container_width=True):
            try:
                proj.rename(new_name=new_proj_name, verbose=verbose)
                st.sidebar.success('Project successfuly renamed.')
                time.sleep(1)
                st.experimental_rerun()
            except FileExistsError:
                col2.error("A project with this name already exists.")
            except FileNotFoundError:
                col2.error("Selected project does not exist.")

        if col1.button('Remove project', use_container_width=True):
            try:
                proj.remove(force=True, verbose=verbose)
                st.sidebar.success('Project successfuly removed.')
                time.sleep(1)
                st.experimental_rerun()
            except FileNotFoundError:
                col2.error("Selected project does not exist.")

with exp_tab:
    if setup_required:
        st.error('Several paths WRFtamer needs haven not been defined. Got to Setup tab or run wt fist_steps.')
    else:
        col1, col2 = st.columns([0.25, 0.75])

        col1.markdown('**Experiment Management**')

        new_exp_name = col1.text_input('New Experiment Name')

        comment_text = col2.text_input(label='Comment', placeholder="Add a brief description of your experiment here")
        uploaded_config_file = col2.file_uploader("Select Configure File", type=['yaml'], accept_multiple_files=False)

        default_message = (
            "To create an experiment, first create an configure.yaml file and select it. You may select "
            "an existing conf file and edit it here. Per default, the name of the configure.yaml "
            "file is used for the experiment name, but you may edit the name if you desire a different "
            'name. Then, click "create experiment" to create a new experiment. You may also '
            "copy-paste the content of a configure.yaml file into this textbox. In any case, a new "
            "configure.yaml file will be stored in your experiment folder."
        )

        if uploaded_config_file:
            uploaded_config_file_value = StringIO(uploaded_config_file.getvalue().decode("utf-8")).read()
            textfield = col2.text_area(label='Configure File', height=400, value=uploaded_config_file_value)
        else:
            textfield = col2.text_area(label='Configure File', height=400, placeholder=default_message)

        if col1.button('Create new experiment'):

            try:

                # writing a temporary config file. The exp_crate command will copy this file to the target directory.
                configfile = db_path / ".temporary_configfile"

                if textfield == "":
                    st.sidebar.error('A config file is required.')
                else:

                    fid = open(configfile, "w")
                    fid.write(textfield)
                    fid.close()

                    proj.exp_create(new_exp_name, comment_text, configfile, namelisttemplate=None, verbose=False)

                    configfile.unlink()
                    st.sidebar.success('Experiment successfuly created.')
                    time.sleep(1)
                    st.experimental_rerun()

            except FileExistsError:
                st.sidebar.error("An experiment with this name already exists. Use a different name or remove the "
                                 "directory first.")

        if col1.button('Rename experiment', use_container_width=True):

            if not exp_name:
                st.sidebar.error('Select experiment to rename.')
            elif new_exp_name == '':
                st.sidebar.error('A new experiment name is required.')
            else:
                try:
                    proj.exp_rename(exp_name, new_exp_name, verbose=False)
                    st.experimental_rerun()
                except FileExistsError:
                    st.sidebar.error("An experiment with the new name already exists.")
                except FileNotFoundError:
                    st.sidebar.error("This experiment does not exist.")
                except ValueError as err_msg:
                    st.sidebar.error(err_msg)

        if col1.button('Remove experiment', use_container_width=True):
            if not exp_name:
                st.sidebar.error('Select experiment to remove.')
            else:
                try:
                    # TODO: a confirmation would be wise.
                    proj.exp_remove(exp_name, force=True, verbose=False)
                    st.sidebar.success('Experiment successfuly removed.')
                    time.sleep(1)
                    st.experimental_rerun()
                except FileNotFoundError:
                    st.sidebar.error("This experiment does not exist and cannot be removed.")

        if col1.button('Copy experiment', use_container_width=True):
            if not exp_name:
                st.sidebar.error('Select experiment to copy.')
            else:
                try:
                    proj.exp_copy(exp_name, new_exp_name, comment_text, verbose=False)
                    st.sidebar.success('Experiment successfuly copied.')
                    time.sleep(1)
                    st.experimental_rerun()
                except FileExistsError:
                    st.sidebar.error("An experiment with the new name alreay exists.")
                except FileNotFoundError:
                    st.sidebar.error("This experiment does not exist.")
                except ValueError as err_msg:
                    st.sidebar.error(err_msg)

        if col1.button('Postprocessing', use_container_width=True):

            if exp_name:
                with st.spinner(f'Running postprocessing for experiment {exp_name}.'):
                    proj.exp_run_postprocessing_protocol(exp_name, verbose=False)
                st.success('Done!')
            else:
                st.sidebar.error('Select Experiment first.')

        if col1.button('Archive Experiment', use_container_width=True):
            keep_log = True  # I may want to add a switch later on?
            if exp_name:
                proj.exp_archive(exp_name, keep_log=keep_log, verbose=False)
                st.sidebar.success('Experiment successfuly archived.')
                time.sleep(1)
                st.experimental_rerun()
            else:
                st.sidebar.error('Select Experiment first.')

with reass_tab:
    if setup_required:
        st.error('Several paths WRFtamer needs haven not been defined. Got to Setup tab or run wt fist_steps.')
    else:

        col1, col2 = st.columns(2)

        selected_exps = col1.multiselect(label='Experiments to reassociate.', options=proj.list_exp())
        target_proj = col2.selectbox('Associate to Project', options=list_projects(verbose=False))

        if st.button('Reassociate'):

            new_proj = Project(target_proj)

            for exp in selected_exps:
                reassociate(proj, new_proj, exp)

            st.sidebar.success('Experiments reassociated.')
            time.sleep(1)
            st.experimental_rerun()

with setup_tab:
    if setup_required:

        st.subheader('Missing setup detected')
        st.markdown('WRFtamer needs a configuration file to run properly. You may create a config file here. '
                    'Once the configuration file has been created, go to step 5 to run the setup command.')

        st.markdown('---')
        st.markdown('**1. Basic configuration**')

        wt_cfg = dict()
        wt_cfg['wrftamer_paths'] = dict()
        wt_cfg['wrftamer_paths']['relative_to_home'] = st.checkbox('Are the following paths relative to $HOME?',
                                                                   value=True)
        wt_cfg['wrftamer_paths']['wrftamer_path'] = st.text_input('the base directory for wrftamer data',
                                                                  placeholder='.wrftamer')
        wt_cfg['wrftamer_paths']['run_path'] = st.text_input('WRF experiments will be created here',
                                                             placeholder='.wrftamer/run')
        wt_cfg['wrftamer_paths']['archive_path'] = st.text_input('archive directory', placeholder='.wrftamer/archive')
        wt_cfg['wrftamer_paths']['plot_path'] = st.text_input('plot directory', placeholder='.wrftamer/plots')
        st.markdown('---')
        st.markdown('**2. Submit Scripts**')
        wt_cfg['wrftamer_make_submit'] = st.checkbox('Should WRFtamer create slurm scripts for job submission? '
                                                     'These scripts may not work for your cluster, depending '
                                                     'on your setup.')

        st.markdown('---')
        st.markdown('**3. WRF and WPS related directories**')
        st.markdown('The WRF and WPS parent directory is the folder where your compiled WRF and WPS code lives, i.e., '
                    'the WRF and WPS repositories to this folder and compile the code.')
        wrf_and_wps_parent_dir = st.text_input('WRF/WPS parent directory',
                                               placeholder='absolute/path/to/WRF/and/WPS/parent/dir')

        wrf_and_wps_parent_dir = Path(wrf_and_wps_parent_dir)
        wrf_dir = wrf_and_wps_parent_dir / 'WRF'
        wps_dir = wrf_and_wps_parent_dir / 'WPS'

        if wrf_dir.is_dir() and wps_dir.is_dir():
            use_wrf_related_features = True
            vtables_avail = list((wrf_and_wps_parent_dir / 'WPS/ungrib/Variable_Tables/').glob('Vtable*'))
            vtables_avail = [item.name for item in vtables_avail]
            vtable = st.selectbox('Select Vtalbe', options=vtables_avail)
        else:
            st.error(f'WRF and WPS directories in {wrf_and_wps_parent_dir} do not exist. Disabling certain features.')
            use_wrf_related_features = False
            vtable = None
            wrf_and_wps_parent_dir = None

        wt_cfg['wrf_and_wps_parent_dir'] = str(wrf_and_wps_parent_dir)
        wt_cfg['vtable'] = vtable
        wt_cfg['use_wrf_related_features'] = use_wrf_related_features

        st.markdown('---')
        st.markdown('**4. Save config file**')

        storage_path = Path(st.text_input('storage path', placeholder=os.environ['HOME']))

        if not storage_path.is_dir():
            st.error('Storage path for config file not found.')
        else:
            config_filename = 'wrftamer_config.yaml'
            command = f'conda env config vars set wrftamer_config={str(storage_path / config_filename)}'

            if st.button('Save Config'):
                with open(storage_path / config_filename, 'w') as f:
                    yaml.safe_dump(wt_cfg, f)

            st.info(f"You need to set the environment variable 'wrftamer_config' manually. Edit the file "
                    f"**{os.environ['CONDA_PREFIX']}/etc/conda/activate.d/env_vars.sh** to set the variable and "
                    f"**{os.environ['CONDA_PREFIX']}/etc/conda/deactivate.d/env_vars.sh** for deactivation.")

            st.markdown(f"**activate**")
            st.code(f"export wrftamer_config={str(storage_path / config_filename)}")
            st.markdown(f"**deactivate**")
            st.code(f"unset wrftamer_config")

        st.markdown('---')
        st.markdown('**5. Run setup command**')

        st.markdown('After the configuration is done, run setup of WRFtamer, which will create '
                    'folders and copy executables and WRF essential files to the run directory. '
                    'This way, every WRF run can be reproduced with ease.')

        try:
            wrf_and_wsp_parent_dir = Path(cfg['wrf_and_wps_parent_dir'])
            vtable = cfg['vtable']
            use_wrf_related_features = cfg['use_wrf_related_features']
            disable_setup = False
        except KeyError:
            st.error('config data not found. You need to save the config file '
                     'and set the environment variable first.')
            disable_setup = True

        if st.button('Run Setup', disabled=disable_setup):

            exe_dir = home_path / "bin/wrf_executables"
            essentials_dir = home_path / "src/wrf_essentials"
            non_essentials_dir = home_path / "src/wrf_nonessentials"
            unassociated_dir = home_path / "db/Unassociated_Experiments"

            if use_wrf_related_features:

                try:
                    wtfun.make_executable_dir(exe_dir, wrf_and_wps_parent_dir)
                    wtfun.make_essential_data_dir(wrf_and_wps_parent_dir, essentials_dir, vtable)
                    wtfun.make_non_essential_data_dir(non_essentials_dir)
                except:
                    st.error('Error encountered during setup of WRF/WPS related directories.')
            else:
                st.info('Usage of WRF/WPS related features turned off.')

            try:
                wtfun.make_unassociated_experiments_dir(unassociated_dir)
            except:
                st.error('Error encountered in make_unassociated_experiments_dir')

    else:
        st.subheader('Information')
        st.markdown(f"WRFtamer, Version {wrftamer.__version__}")
        st.markdown(f'**WRFtamer Path:** {db_path}')
        st.markdown(f'**Run directory:** {run_path}')
        st.markdown(f'**Archive directory:** {archive_path}')
        st.markdown(f'**Plot directory:** {plot_path}')
        #st.markdown(f'**Poi file:** {poi_file}')
        #st.markdown(f'**Your levels per variable-file:** {levs_per_var_file}')

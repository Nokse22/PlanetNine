pkgdatadir = get_option('prefix') / get_option('datadir') / meson.project_name()
moduledir = pkgdatadir / 'planetnine'
gnome = import('gnome')

gnome.compile_resources('planetnine',
  'planetnine.gresource.xml',
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
)

python = import('python')

conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').full_path())
conf.set('VERSION', meson.project_version())
conf.set('localedir', get_option('prefix') / get_option('localedir'))
conf.set('pkgdatadir', pkgdatadir)

configure_file(
  input: 'planetnine.in',
  output: 'planetnine',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir'),
  install_mode: 'r-xr-xr-x'
)

planetnine_sources = [
  '__init__.py',
  'main.py',
  'window.py',

  'models/cell.py',
  'models/output.py',
  'models/notebook.py',

  'pages/notebook_page.py',
  'pages/browser_page.py',
  'pages/console_page.py',
  'pages/code_page.py',

  'widgets/image_view.py',
  'widgets/kernel_manager_view.py',
  'widgets/workspace_view.py',
  'widgets/launcher.py',
  'widgets/console_cell.py',
  'widgets/tree_row_widget.py',
  'widgets/markdown_textview.py',
  'widgets/terminal_textview.py',
  'widgets/cell_ui.py',
  'widgets/json_viewer.py',

  'utils/async_helpers.py',
  'utils/converters.py',
  'utils/utilities.py',

  'completion_providers/completion_providers.py',

  'backend/command_line.py',
  'backend/jupyter_kernel.py',
  'backend/jupyter_server.py',

  'others/notebook_save_delegate.py',
  'others/preferences.py',
]

install_data(planetnine_sources, install_dir: moduledir)

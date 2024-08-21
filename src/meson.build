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
  'cell.py',
  'cell_ui.py',
  'output.py',
  'markdown_textview.py',
  'terminal_textview.py',
  'notebook.py',
  'notebook_page.py',
  'browser_page.py',
  'image_view.py',
  'kernel_manager_view.py',
  'workspace_view.py',
  'launcher.py',
  'console_page.py',
  'console_cell.py',
  'code_page.py',
  'tree_row_widget.py',

  'notebook_save_delegate.py',

  'async_helpers.py',
  'converters.py',

  'completion_providers.py',

  'backend/command_line.py',
  'backend/jupyter_kernel.py',
  'backend/jupyter_server.py',
]

install_data(planetnine_sources, install_dir: moduledir)

test_data = [
  'data/json_display.ipynb'
]

install_data(test_data, install_dir: join_paths(meson.current_build_dir(), 'data'))

envdata = environment()
python_paths = [join_paths(meson.current_build_dir(), '..')]
envdata.append('PYTHONPATH', python_paths)
envdata.append('TESTS_BUILDDIR', meson.current_build_dir())

pytest_exe = find_program('pytest', required: false)
if pytest_exe.found()
    test(
        'Pytest',
        pytest_exe,
        args: [meson.project_source_root() + '/', '-s'],
        suite: 'pytest',
        env: envdata,
        workdir: join_paths(meson.project_source_root(), 'tests')
    )
endif
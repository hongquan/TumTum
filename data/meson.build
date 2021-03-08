

install_data(['tumtum.glade', 'about.glade', 'url-display.glade', 'wifi-display.glade',
              'tumtum_128.png', 'wireframe-image-add.svg'],
  install_dir: get_option('datadir') / meson.project_name()
)


desktop_file = 'vn.hoabinh.quan.TumTum.desktop'

desktop_utils = find_program('desktop-file-validate', required: false)
if desktop_utils.found()
  test('Validate desktop file', desktop_utils,
    args: [desktop_file]
  )
  install_data(desktop_file,
    install_dir: get_option('datadir') / 'applications'
  )
endif

themedir = get_option('datadir') / 'icons/hicolor'
install_data('vn.hoabinh.quan.TumTum.svg',
  install_dir: themedir / 'scalable/apps'
)

appstream_file = 'vn.hoabinh.quan.TumTum.appdata.xml'

appstream_util = find_program('appstream-util', required: false)
if appstream_util.found()
  test('Validate appstream file', appstream_util,
    args: ['validate', appstream_file]
  )
  install_data(appstream_file,
    install_dir: get_option('datadir') / 'metainfo'
  )
endif

install_data('vn.hoabinh.quan.TumTum.gschema.xml',
  install_dir: get_option('datadir') / 'glib-2.0/schemas'
)

compile_schemas = find_program('glib-compile-schemas', required: false)
if compile_schemas.found()
  test('Validate schema file', compile_schemas,
    args: ['--strict', '--dry-run', meson.current_source_dir()]
  )
endif

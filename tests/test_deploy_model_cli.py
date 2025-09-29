from pathlib import Path

from scripts.deployment import deploy_model


def test_slugify_project_produces_clean_slug():
    assert deploy_model.slugify_project('Rooftop Scan 01!') == 'rooftop-scan-01'
    assert deploy_model.slugify_project('   ') == 'model'
    assert deploy_model.slugify_project('A' * 80).startswith('a' * 48)


def test_collect_upload_items_from_single_file(tmp_path: Path):
    html = tmp_path / 'viewer.html'
    html.write_text('<html></html>', encoding='utf-8')

    items, root, entry_key = deploy_model.collect_upload_items(html, 'models', 'demo-hash', entrypoint=None)

    assert root == tmp_path
    assert len(items) == 1
    upload = items[0]
    assert upload.dest_key == 'models/demo-hash/viewer.html'
    assert upload.source == html
    assert entry_key == 'models/demo-hash/viewer.html'


def test_collect_upload_items_from_directory(tmp_path: Path):
    bundle = tmp_path / 'bundle'
    bundle.mkdir()
    (bundle / 'index.html').write_text('<html></html>', encoding='utf-8')
    assets = bundle / 'assets'
    assets.mkdir()
    (assets / 'main.js').write_text('console.log("ok")', encoding='utf-8')
    (assets / 'styles.css').write_text('body{}', encoding='utf-8')

    items, root, entry_key = deploy_model.collect_upload_items(bundle, 'deliveries', 'scan-123', entrypoint=None)

    assert root == bundle
    keys = sorted(item.dest_key for item in items)
    assert keys == [
        'deliveries/scan-123/assets/main.js',
        'deliveries/scan-123/assets/styles.css',
        'deliveries/scan-123/index.html',
    ]
    assert {item.source for item in items} == {
        bundle / 'index.html',
        assets / 'main.js',
        assets / 'styles.css',
    }
    assert entry_key == 'deliveries/scan-123/index.html'


def test_build_hash_is_deterministic(tmp_path: Path):
    file_a = tmp_path / 'a.html'
    file_a.write_text('<html></html>', encoding='utf-8')
    file_b = tmp_path / 'b.js'
    file_b.write_text('console.log(42);', encoding='utf-8')

    hash_one = deploy_model.build_hash([file_a, file_b], 8)
    hash_two = deploy_model.build_hash([file_b, file_a], 8)

    assert hash_one == hash_two
    assert len(hash_one) == 8

# 1b. Dataset VERSIONS the input panel cannot pick (Kaggle attaches only a dataset's latest version): downloaded with
#     kagglehub (needs Settings -> Internet ON). gen-extra-all version 1 = the extra run (55 ours + 44 OOD-45); its
#     samples output was replaced by the combined run's, so its samples are rebuilt here.
DOWNLOAD = ['ziadsamer/gen-extra-all/versions/1']
DOWNLOADED = []
if DOWNLOAD:
    import kagglehub
    for ref in DOWNLOAD:
        DOWNLOADED.append(kagglehub.dataset_download(ref))
        print('downloaded', ref, '->', DOWNLOADED[-1], sorted(p.name for p in Path(DOWNLOADED[-1]).rglob('*') if p.is_file())[:6], flush=True)

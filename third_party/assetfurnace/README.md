# AssetFurnace

[AssetFurnace](https://github.com/Bingeljell/image-to-3dlab) (Apache-2.0) is lochara's picture → 3D step: a local
studio around several image-to-3D engines, with Finish (cleanup to a triangle count) and an agent API.

`lochara setup assetfurnace` clones release **v0.5.7** into `vendor/assetfurnace`, runs that release's own
installer (the one on assetfurnace.com tracks `main` and expects files v0.5.7 doesn't have), and applies
`backend-spec.patch`.

## backend-spec.patch
In v0.5.7 (and on `main` as of 2026-11-08), the job runner looks engines up with `BACKENDS[job.backend_id]`. The
studio sends the catalogue id (`hunyuan_xiong`) but the generator is keyed `hunyuan-mlx-xiong`, so the job thread
dies with a `KeyError` while the studio keeps reporting "Working…". The module already has `backend_spec()`,
which resolves the alias (their issue #151); the patch uses it in the two places that didn't.

Worth reporting upstream; drop the patch when a release includes the fix.

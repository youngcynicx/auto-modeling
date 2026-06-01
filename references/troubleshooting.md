# Troubleshooting

## CadQuery Import Fails

Activate the virtual environment or run the setup script:

```bash
. .venv/bin/activate
python -m pip install cadquery==2.7.0
```

## Boolean Operation Fails

- Increase cutter overlap by `0.1` to `0.5` mm.
- Avoid coplanar faces by extending cutters beyond the target solid.
- Apply `clean()` after unions and cuts.
- Split complex operations into multiple simpler cuts.
- Build cutaways before adding helical threads when possible.

## Thread Sweep Fails

- Reduce profile size or avoid self-intersection.
- Confirm helix radius is positive and larger than the profile radial radius.
- Try a rounded ellipse profile before triangular profiles.
- Use a visual simplified thread if the user does not need functional thread geometry.

## STL Export Is Too Heavy

Increase STL tolerance:

```python
cq.exporters.export(model, str(stl_path), tolerance=0.1, angularTolerance=0.2)
```

## Model Looks Solid But Internal Channels Are Missing

- Confirm cutters extend past the outer faces.
- Verify workplane axis and offset.
- Add a cutaway artifact to inspect internal geometry.
- Make one channel at a time until the failure is isolated.

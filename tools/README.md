Copy background image into project

1. Save your attached image locally (e.g., Downloads) as `bg.jpg` or any name.
2. From the project root run:

```
python tools\add_bg_from_path.py "C:\path\to\your\image.jpg"
```

This will copy the file to `repairs/static/repairs/bg.jpg`.

After copying, restart the dev server and refresh the login page.

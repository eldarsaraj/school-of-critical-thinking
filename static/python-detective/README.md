# Python Detective - Interactive Course Site

## What You Have

This is a fully functional, interactive Python learning site that matches your School of Critical Thinking aesthetic. Students can:
- Read lessons in your site's style
- Run Python code directly in the browser (no installation needed)
- Experiment and modify code
- Complete all exercises interactively

## Files Structure

```
python-detective/
├── index.html          # Landing page with all 15 lessons listed
├── lesson-01.html      # Complete Lesson 1 with executable code cells
├── style.css           # Matches your site's aesthetic exactly
└── README.md           # This file
```

## How It Works

**Technology:** Uses Pyodide (Python compiled to WebAssembly) to run Python directly in the browser. No server needed, no installation required for students.

**Design:** Matches your School of Critical Thinking site exactly:
- Same paper texture background (#FFFEF8)
- Same fonts (Helvetica, Arial)
- Same subtle borders and spacing
- Same restrained, academic aesthetic
- Fully responsive

## Testing Locally

### Option 1: Simple Python Server (Easiest)

1. Open Terminal/Command Prompt
2. Navigate to the python-detective folder:
   ```bash
   cd /path/to/python-detective
   ```
3. Run a local server:
   ```bash
   python3 -m http.server 8000
   ```
4. Open browser and go to: `http://localhost:8000`

### Option 2: VS Code Live Server

1. Open the python-detective folder in VS Code
2. Install "Live Server" extension if you don't have it
3. Right-click on index.html
4. Select "Open with Live Server"

### Option 3: Direct File Opening (May Have Limitations)

Simply double-click `index.html` to open in browser. Note: Code execution may not work due to CORS restrictions. Use Option 1 or 2 for full functionality.

## Deploying to Your Django Site

### Method 1: Static Files (RECOMMENDED - Safest)

This keeps Python Detective completely separate from your Django app:

1. **Upload the folder to your server:**
   - If you use FTP/SFTP: Upload the entire `python-detective` folder to your web root
   - The folder should be at the same level as your Django project, not inside it

2. **Access it directly:**
   - Your site will be available at: `schoolofcriticalthinking.org/python-detective/`
   - No Django configuration needed
   - Can't break your existing site

3. **If using shared hosting:**
   - Upload to `public_html/python-detective/` or similar
   - Accessible at your domain + /python-detective/

### Method 2: Through Django Static Files

If you want it served through Django:

1. **Copy to your Django static directory:**
   ```
   your_django_project/
   ├── static/
   │   └── python-detective/
   │       ├── index.html
   │       ├── lesson-01.html
   │       └── style.css
   ```

2. **Add URL pattern** in your `urls.py`:
   ```python
   from django.urls import path
   from django.views.generic import RedirectView

   urlpatterns = [
       # Your existing URLs...
       path('python-detective/', 
            RedirectView.as_view(url='/static/python-detective/index.html', 
                               permanent=False)),
   ]
   ```

3. **Run collectstatic:**
   ```bash
   python manage.py collectstatic
   ```

### Method 3: As Django Templates (If You Want Full Integration)

Only do this if you want to add Django features like user auth, progress tracking, etc.

1. Copy HTML files to your templates directory
2. Convert to Django templates (add {% load static %}, etc.)
3. Create views and URLs

**Recommendation:** Start with Method 1 or 2. They're simpler and safer.

## Customization

### Linking to Your Actual Site

In both `index.html` and `lesson-01.html`, update these links:

```html
<!-- Current placeholder links -->
<a href="https://schoolofcriticalthinking.org">Home</a>
<a href="https://schoolofcriticalthinking.org/articles">Articles</a>

<!-- Update with your actual URLs -->
<a href="https://schoolofcriticalthinking.org">Home</a>
<a href="https://schoolofcriticalthinking.org/articles">Articles</a>
```

### Adding Your Logo

Replace this in the header:
```html
<div class="logo">
  <a href="https://schoolofcriticalthinking.org">
    <span style="font-size: 12px; letter-spacing: 0.12em; text-transform: uppercase; color: rgba(0,0,0,0.7);">School of Critical Thinking</span>
  </a>
</div>
```

With:
```html
<div class="logo">
  <a href="https://schoolofcriticalthinking.org">
    <img src="path/to/your/logo.png" alt="School of Critical Thinking">
  </a>
</div>
```

## Building the Remaining 14 Lessons

You have Lesson 1 as a complete template. To create the other lessons:

1. Copy `lesson-01.html` to `lesson-02.html`, `lesson-03.html`, etc.
2. Update the content based on your Word document syllabus
3. Keep the same structure:
   - Lesson header with meta and objectives
   - Sections with labels
   - Code cells with the `runCode()` function
   - Info boxes for tips and exercises
   - Lesson navigation at the bottom

### Code Cell Template

```html
<div class="code-cell">
  <div class="code-cell__input">
    <pre># Your Python code here
print("Hello, World!")</pre>
  </div>
  <button class="code-cell__run" onclick="runCode(this, X)">▶ Run Code</button>
  <div class="code-cell__output" id="output-X" style="display: none;"></div>
</div>
```

**Important:** Each code cell needs a unique number (X). Increment for each cell on the page.

## Browser Support

**Works in:**
- Chrome/Edge (recommended)
- Firefox
- Safari (may be slower)

**Requires:**
- JavaScript enabled
- Modern browser (2020+)
- Internet connection (to load Pyodide on first visit)

## Performance Notes

- First code execution takes 3-5 seconds (loading Python)
- Subsequent executions are instant
- Pyodide loads once per page visit
- No data is sent to servers - runs 100% in browser

## Troubleshooting

### Code won't run
- Check browser console for errors
- Make sure you're using a web server (not file://)
- Try Chrome if using another browser

### Styling looks wrong
- Clear browser cache
- Make sure style.css is loading (check Network tab)
- Verify file paths are correct

### Input prompts not working
- This is normal - browser prompts are used instead of console input
- Works the same way, just in a popup

## Next Steps

1. **Test locally** - Make sure everything works on your computer
2. **Get feedback** - Show a few kids, see if they can use it
3. **Deploy** - Upload to your server using Method 1
4. **Build lessons 2-15** - Use lesson-01.html as template
5. **Iterate** - Improve based on user feedback

## Future Enhancements (Optional)

Once the core site is working, you could add:
- Progress tracking (requires Django backend)
- Code sharing (copy code to clipboard button)
- Dark mode toggle
- Printable worksheets
- Video walkthroughs
- Discussion forums
- Certificates of completion

## Questions?

If you run into issues:
1. Check the browser console (F12) for errors
2. Verify file paths are correct
3. Make sure you're using a web server for local testing
4. Test in Chrome first (best Pyodide support)

## License & Credits

- Pyodide: https://pyodide.org (Python in the browser)
- Design: Matches School of Critical Thinking aesthetic
- Content: Original curriculum by Eldar Sarajlic

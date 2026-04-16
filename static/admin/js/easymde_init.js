document.addEventListener('DOMContentLoaded', function () {
  var el = document.getElementById('id_content_markdown');
  if (!el || typeof EasyMDE === 'undefined') return;

  new EasyMDE({
    element: el,
    spellChecker: false,
    minHeight: '520px',
    autosave: {
      enabled: true,
      uniqueId: 'article-content-markdown',
      delay: 3000,
    },
    toolbar: [
      'bold', 'italic', 'heading', '|',
      'quote', 'unordered-list', 'ordered-list', '|',
      'link', 'image', '|',
      'preview', 'side-by-side', 'fullscreen', '|',
      'guide',
    ],
    renderingConfig: {
      singleLineBreaks: false,
    },
  });
});

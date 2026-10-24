# Where the files go
Copy the 7 .html files into your static folder at:
    static/widgets/adaptive-tests/
(then run `python manage.py collectstatic` if your site uses it)

# What to paste in the markdown, at each "Fig." spot
(Each widget now shows its own "Fig. N" title, so remove the plain-text title line from the article.)

Fig. 1
<iframe class="sct-widget" src="/static/widgets/adaptive-tests/fig1-question-paths.html" title="Which questions each student sees" loading="lazy" scrolling="no" style="width:100%;height:365px;border:0;display:block;margin:24px 0;"></iframe>

Fig. 2
<iframe class="sct-widget" src="/static/widgets/adaptive-tests/fig2-ceiling-floor.html" title="Difficulty has a ceiling and a floor" loading="lazy" scrolling="no" style="width:100%;height:365px;border:0;display:block;margin:24px 0;"></iframe>

Fig. 3
<iframe class="sct-widget" src="/static/widgets/adaptive-tests/fig3-difficulty.html" title="Difficulty: one question, three students" loading="lazy" scrolling="no" style="width:100%;height:475px;border:0;display:block;margin:24px 0;"></iframe>

Fig. 4
<iframe class="sct-widget" src="/static/widgets/adaptive-tests/fig4-discrimination.html" title="Discrimination: same difficulty, different steepness" loading="lazy" scrolling="no" style="width:100%;height:500px;border:0;display:block;margin:24px 0;"></iframe>

Fig. 5
<iframe class="sct-widget" src="/static/widgets/adaptive-tests/fig5-calibration.html" title="Calibrating one question" loading="lazy" scrolling="no" style="width:100%;height:645px;border:0;display:block;margin:24px 0;"></iframe>

Fig. 6
<iframe class="sct-widget" src="/static/widgets/adaptive-tests/fig6-adaptive-test.html" title="A small adaptive test" loading="lazy" scrolling="no" style="width:100%;height:675px;border:0;display:block;margin:24px 0;"></iframe>

Fig. 7
<iframe class="sct-widget" src="/static/widgets/adaptive-tests/fig7-same-score.html" title="Same number right, different estimates" loading="lazy" scrolling="no" style="width:100%;height:325px;border:0;display:block;margin:24px 0;"></iframe>

# Paste once, at the very end of the article (optional but recommended)
It makes each widget exactly as tall as its content on any screen size.
If your markdown strips scripts, skip it: the heights above are set so nothing gets cut off.

<script>
window.addEventListener('message', function (e) {
  if (!e.data || e.data.type !== 'sct-widget-height') return;
  document.querySelectorAll('iframe.sct-widget').forEach(function (f) {
    if (f.contentWindow === e.source) f.style.height = e.data.height + 'px';
  });
});
</script>

/* Home page: previous/next buttons for the More to play row.
   The row also scrolls natively (swipe or scrollbar). No autoplay. */
(function () {
    var root = document.querySelector('.daily-picks');
    if (!root) return;

    var scroller = root.querySelector('.daily-picks-row');
    var prev = root.querySelector('.daily-picks-prev');
    var next = root.querySelector('.daily-picks-next');
    if (!scroller || !prev || !next) return;

    function prefersReducedMotion() {
        return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    }

    function update() {
        var max = Math.max(0, scroller.scrollWidth - scroller.clientWidth);
        var canScroll = max > 1;
        prev.hidden = !canScroll;
        next.hidden = !canScroll;
        if (!canScroll) return;
        prev.disabled = scroller.scrollLeft <= 1;
        next.disabled = scroller.scrollLeft >= max - 1;
    }

    function scrollByDir(direction) {
        var amount = Math.max(scroller.clientWidth * 0.8, 200);
        scroller.scrollBy({
            left: direction * amount,
            behavior: prefersReducedMotion() ? 'auto' : 'smooth'
        });
    }

    prev.addEventListener('click', function () { scrollByDir(-1); });
    next.addEventListener('click', function () { scrollByDir(1); });
    scroller.addEventListener('scroll', update, { passive: true });
    window.addEventListener('resize', update);
    if (typeof ResizeObserver === 'function') {
        new ResizeObserver(update).observe(scroller);
    }
    update();
})();

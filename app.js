let currentCategory = localStorage.getItem('selectedCategory') || 'books';
let isLoading = false;
const dataCache = {
    books: null,
    anime: null
};

const DOMCache = {
    container: null,
    tabs: null,
    indicator: null,
    stats: null,
    bookList: null
};

let intersectionObserver = null;

function initDOMCache() {
    DOMCache.container = document.querySelector('.container');
    DOMCache.tabs = document.querySelectorAll('.tab-btn');
    DOMCache.indicator = document.getElementById('tab-indicator');
    DOMCache.stats = document.getElementById('total-books');
    DOMCache.bookList = document.getElementById('book-list');
}

document.addEventListener('DOMContentLoaded', () => {
    initDOMCache();
    syncTabUI(currentCategory);
    fetchData(currentCategory);
    initSmoothScroll();
    initTabs();
});

function syncTabUI(category) {
    DOMCache.tabs.forEach(tab => {
        if (tab.getAttribute('data-category') === category) {
            tab.classList.add('active');
            requestAnimationFrame(() => updateIndicator(tab, DOMCache.indicator));
        } else {
            tab.classList.remove('active');
        }
    });
}

function updateIndicator(activeTab, indicator) {
    if (!activeTab || !indicator) return;
    const rect = activeTab.getBoundingClientRect();
    const containerRect = activeTab.parentElement.getBoundingClientRect();
    
    indicator.style.width = `${rect.width}px`;
    indicator.style.transform = `translateX(${rect.left - containerRect.left - 4}px)`;
}

function initTabs() {
    DOMCache.tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const category = tab.getAttribute('data-category');
            if (category === currentCategory || isLoading) return;

            isLoading = true;

            DOMCache.tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            updateIndicator(tab, DOMCache.indicator);

            currentCategory = category;
            localStorage.setItem('selectedCategory', category);
            fetchData(category).finally(() => {
                isLoading = false;
            });
        });
    });

    let resizeTimeout;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(() => {
            const activeTab = document.querySelector('.tab-btn.active');
            updateIndicator(activeTab, DOMCache.indicator);
        }, 100);
    }, { passive: true });
}

function initSmoothScroll() {
    const lenis = new Lenis({
        duration: 1.2,
        lerp: 0.1,
        easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
        orientation: 'vertical',
        gestureOrientation: 'vertical',
        smoothWheel: true,
        wheelMultiplier: 1.1,
        touchMultiplier: 2,
    });

    function raf(time) {
        lenis.raf(time);
        requestAnimationFrame(raf);
    }

    requestAnimationFrame(raf);
}

async function fetchData(category) {
    const container = DOMCache.bookList;
    
    if (dataCache[category]) {
        await crossFade(container, () => renderItems(dataCache[category]));
        updateStats(dataCache[category].length, category);
        return;
    }

    await crossFade(container, async () => {
        container.innerHTML = `
            <div class="skeleton-card">
                <div class="skeleton-text" style="width: 20px; height: 12px; margin-top: 6px;"></div>
                <div class="skeleton-cover"></div>
                <div class="skeleton-content">
                    <div class="skeleton-text" style="width: 40%"></div>
                    <div class="skeleton-text" style="width: 80%; height: 32px"></div>
                    <div class="skeleton-text" style="width: 60%"></div>
                </div>
            </div>
        `;
        
        try {
            const response = await fetch(`${category}.json`);
            const data = await response.json();
            dataCache[category] = data;
            renderItems(data);
            updateStats(data.length, category);
        } catch (error) {
            console.error('Error fetching data:', error);
            container.innerHTML = `<div class="loading-state">Failed to load ${category}.</div>`;
        }
    });
}

function crossFade(container, callback) {
    return new Promise(resolve => {
        container.style.transition = 'opacity 0.25s ease-out';
        container.style.opacity = '0';
        
        setTimeout(async () => {
            await callback();
            container.style.opacity = '1';
            setTimeout(resolve, 250);
        }, 250);
    });
}

function renderItems(items) {
    const container = DOMCache.bookList;
    
    container.style.opacity = '1';
    
    const fragment = document.createDocumentFragment();
    const isOnePieceIndex = items.findIndex(item => item.title === 'One Piece');

    items.forEach((item, index) => {
        const isOnePiece = index === isOnePieceIndex && isOnePieceIndex !== -1;
        const cardClass = isOnePiece ? 'book-card is-legendary' : 'book-card';
        const titleClass = isOnePiece ? 'book-title shimmer-text' : 'book-title';
        
        const element = document.createElement('article');
        element.className = cardClass;
        
        const number = (index + 1).toString().padStart(2, '0');
        const ratingDisplay = item.rating_text || "TBR";
        const ratingClass = !item.rating_text ? "rating-text tbr" : "rating-text";
        const loadingAttr = index < 3 ? 'loading="eager"' : 'loading="lazy"';
        
        const titleHtml = isOnePiece ? `
            <div class="legendary-title-container">
                <h2 class="${titleClass}">${item.title}</h2>
                <div class="text-sparkles">
                    <div class="t-sparkle"></div>
                    <div class="t-sparkle"></div>
                    <div class="t-sparkle"></div>
                </div>
            </div>
        ` : `<h2 class="${titleClass}">${item.title}</h2>`;
        
        element.innerHTML = `
            <div class="book-index">${number}</div>
            <div class="book-cover-container">
                <img data-src="${item.cover_url}" alt="${item.title}" class="book-cover" ${loadingAttr}>
            </div>
            <div class="book-content">
                <div class="book-meta">
                    <span class="${ratingClass}">${ratingDisplay}</span>
                </div>
                ${titleHtml}
                <div class="book-author">by ${item.author || 'Unknown'}</div>
            </div>
            ${isOnePiece ? `
                <div class="legendary-visual">
                    <img src="assets/covers/anime/luffy-peak.gif" alt="Luffy Legendary" loading="lazy">
                </div>
            ` : ''}
        `;
        
        fragment.appendChild(element);
    });

    container.innerHTML = '';
    container.appendChild(fragment);

    if (intersectionObserver) {
        intersectionObserver.disconnect();
    }

    intersectionObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                
                const img = entry.target.querySelector('img[data-src]');
                if (img) {
                    img.src = img.dataset.src;
                    img.onload = () => img.classList.add('loaded');
                    img.onerror = () => {
                        img.parentElement.innerHTML = `<div class="skeleton-cover" style="background:#111; display:flex; align-items:center; justify-content:center; font-size:0.6rem; color:#333; font-family:var(--font-mono);">ERROR</div>`;
                    };
                    delete img.dataset.src;
                }
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: '50px'
    });

    container.querySelectorAll('.book-card').forEach(card => intersectionObserver.observe(card));
}

function updateStats(count, category) {
    if (DOMCache.stats) {
        const label = category === 'books' ? 'Book' : 'Anime';
        DOMCache.stats.textContent = `${count} ${label}${count !== 1 ? "s" : ""}`;
    }
}

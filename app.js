let currentCategory = localStorage.getItem('selectedCategory') || 'books';
const dataCache = {
    books: null,
    anime: null
};

document.addEventListener('DOMContentLoaded', () => {
    syncTabUI(currentCategory);
    fetchData(currentCategory);
    initSmoothScroll();
    initTabs();
});

function syncTabUI(category) {
    const tabs = document.querySelectorAll('.tab-btn');
    const indicator = document.getElementById('tab-indicator');
    
    tabs.forEach(tab => {
        if (tab.getAttribute('data-category') === category) {
            tab.classList.add('active');
            // Small delay to ensure DOM is ready for rect calculation
            setTimeout(() => updateIndicator(tab, indicator), 10);
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
    const tabs = document.querySelectorAll('.tab-btn');
    const indicator = document.getElementById('tab-indicator');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const category = tab.getAttribute('data-category');
            if (category === currentCategory) return;

            // Update UI
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            updateIndicator(tab, indicator);

            currentCategory = category;
            localStorage.setItem('selectedCategory', category);
            fetchData(category);
        });
    });

    window.addEventListener('resize', () => {
        const activeTab = document.querySelector('.tab-btn.active');
        updateIndicator(activeTab, indicator);
    });
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

    lenis.on('scroll', ({ velocity }) => {
        const skew = Math.min(Math.max(velocity * 0.05, -2.5), 2.5);
        document.querySelectorAll('.book-card.visible').forEach(card => {
            card.style.transform = `skewY(${skew}deg)`;
        });
    });

    let mouseX = 0, mouseY = 0;
    window.addEventListener('mousemove', (e) => {
        mouseX = e.clientX;
        mouseY = e.clientY;
    });

    function raf(time) {
        lenis.raf(time);
        document.documentElement.style.setProperty('--x', `${mouseX}px`);
        document.documentElement.style.setProperty('--y', `${mouseY}px`);
        requestAnimationFrame(raf);
    }

    requestAnimationFrame(raf);
}

async function fetchData(category) {
    const container = document.getElementById('book-list');
    
    if (dataCache[category]) {
        renderItems(dataCache[category]);
        updateStats(dataCache[category].length, category);
        return;
    }

  // Show skeleton while loading
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
}

function renderItems(items) {
    const container = document.getElementById('book-list');
    
    // Smooth container fade-out before replacement
    container.style.opacity = '1';
    
    const fragment = document.createDocumentFragment();

    items.forEach((item, index) => {
        const isOnePiece = item.title === 'One Piece';
        const cardClass = isOnePiece ? 'book-card is-legendary' : 'book-card';
        const titleClass = isOnePiece ? 'book-title shimmer-text' : 'book-title';
        
        const element = document.createElement('article');
        element.className = cardClass;
        
        const number = (index + 1).toString().padStart(2, '0');
        const ratingDisplay = item.rating_text || "TBR";
        const ratingClass = !item.rating_text ? "rating-text tbr" : "rating-text";
        
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
                <img data-src="${item.cover_url}" alt="${item.title}" class="book-cover">
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
                    <img src="assets/covers/anime/luffy-peak.gif" alt="Luffy Legendary">
                </div>
            ` : ''}
        `;
        
        fragment.appendChild(element);
    });

    container.innerHTML = '';
    container.appendChild(fragment);

    // Initialize Intersection Observer for reveals
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                
                // Lazy load image inside
                const img = entry.target.querySelector('img');
                if (img && img.dataset.src) {
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

    document.querySelectorAll('.book-card').forEach(card => observer.observe(card));
}

function updateStats(count, category) {
    const statsEl = document.getElementById('total-books');
    if (statsEl) {
        const label = category === 'books' ? 'Book' : 'Anime';
        statsEl.textContent = `${count} ${label}${count !== 1 ? "s" : ""}`;
    }
}

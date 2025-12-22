document.addEventListener('DOMContentLoaded', () => {
    fetchBooks();
    initSmoothScroll();
});

function initSmoothScroll() {
    const lenis = new Lenis({
        duration: 1.2,
        lerp: 0.1, // Smoothness factor
        easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
        orientation: 'vertical',
        gestureOrientation: 'vertical',
        smoothWheel: true,
        wheelMultiplier: 1,
        smoothTouch: false,
    });

    // Handle Snap logic on stop
    lenis.on('scroll', ({ velocity, isScrolling }) => {
        // Skew effect
        const skew = velocity * 0.05;
        const cards = document.querySelectorAll('.book-card');
        cards.forEach(card => {
            const currentSkew = Math.min(Math.max(skew, -2), 2);
            card.style.transform = `skewY(${currentSkew}deg)`;
        });
    });

    // Spotlight Effect - Throttled for performance
    let mouseX = 0, mouseY = 0;
    window.addEventListener('mousemove', (e) => {
        mouseX = e.clientX;
        mouseY = e.clientY;
    });

    function raf(time) {
        lenis.raf(time);
        
        // Update spotlight position in RAF
        document.documentElement.style.setProperty('--x', `${mouseX}px`);
        document.documentElement.style.setProperty('--y', `${mouseY}px`);
        
        requestAnimationFrame(raf);
    }

    requestAnimationFrame(raf);
}

async function fetchBooks() {
    try {
        const response = await fetch('books.json');
        const books = await response.json();
        renderBooks(books);
        updateStats(books.length);
    } catch (error) {
        console.error('Error fetching books:', error);
        document.getElementById('book-list').innerHTML = `
            <div class="loading-state">
                Failed to load library. Please ensure books.json is valid.
            </div>
        `;
    }
}

function renderBooks(books) {
    const container = document.getElementById('book-list');
    container.innerHTML = '';

    books.forEach((book, index) => {
        const bookElement = document.createElement('article');
        bookElement.className = 'book-card';
        bookElement.style.animationDelay = `${index * 0.1}s`;
        
        const bookNumber = (index + 1).toString().padStart(2, '0');
        const isTBR = !book.rating_text || book.rating_text.trim() === "";
        const ratingDisplay = isTBR ? "TBR" : book.rating_text;
        const ratingClass = isTBR ? "rating-text tbr" : "rating-text";
        
        bookElement.innerHTML = `
            <div class="book-index">${bookNumber}</div>
            ${book.cover_url ? `
                <div class="book-cover-container">
                    <img src="${book.cover_url}" 
                         alt="${book.title}" 
                         class="book-cover" 
                         loading="lazy" 
                         decoding="async">
                </div>` : ''}
            <div class="book-content">
                <div class="book-meta">
                    <span class="${ratingClass}">${ratingDisplay}</span>
                </div>
                <h2 class="book-title">${book.title}</h2>
                <div class="book-author">by ${book.author}</div>
            </div>
        `;
        
        container.appendChild(bookElement);
    });
}

function updateStats(count) {
    const statsEl = document.getElementById('total-books');
    if (statsEl) {
        statsEl.textContent = `${count} Book${count !== 1 ? 's' : ''}`;
    }
}

function formatDate(dateStr) {
    if (!dateStr) return 'Unknown';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

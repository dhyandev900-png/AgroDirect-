// Smooth scroll reveal animation
document.addEventListener("DOMContentLoaded", function() {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-fade-in');
            }
        });
    }, { threshold: 0.1 });

    document.querySelectorAll('.premium-card, .step-card').forEach((el) => {
        el.style.opacity = '0';
        observer.observe(el);
    });
});
/**
 * Aura WebGL / Canvas Dot-Matrix Background Field
 * Renders an atmospheric, technical dot-matrix particle grid with slow breathing pulse and subtle pointer drift.
 */
(function() {
    function initMatrixField() {
        const canvas = document.getElementById('webgl-canvas');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        let width = (canvas.width = window.innerWidth);
        let height = (canvas.height = window.innerHeight);

        let mouse = { x: width / 2, y: height / 2, targetX: width / 2, targetY: height / 2 };
        let dots = [];
        const spacing = 32;

        function createGrid() {
            dots = [];
            width = canvas.width = window.innerWidth;
            height = canvas.height = window.innerHeight;

            const cols = Math.ceil(width / spacing);
            const rows = Math.ceil(height / spacing);

            for (let r = 0; r <= rows; r++) {
                for (let c = 0; c <= cols; c++) {
                    dots.push({
                        baseX: c * spacing,
                        baseY: r * spacing,
                        phase: Math.random() * Math.PI * 2,
                        speed: 0.0015 + Math.random() * 0.001
                    });
                }
            }
        }

        createGrid();

        window.addEventListener('resize', createGrid, { passive: true });
        window.addEventListener('mousemove', (e) => {
            mouse.targetX = e.clientX;
            mouse.targetY = e.clientY;
        }, { passive: true });

        let time = 0;
        function animate() {
            time += 0.015;
            mouse.x += (mouse.targetX - mouse.x) * 0.04;
            mouse.y += (mouse.targetY - mouse.y) * 0.04;

            ctx.clearRect(0, 0, width, height);

            const isDark = document.documentElement.getAttribute('data-theme') !== 'light';
            const baseAlpha = isDark ? 0.28 : 0.18;
            const primaryColor = '16, 185, 129'; // Emerald

            for (let i = 0; i < dots.length; i++) {
                const dot = dots[i];
                const dx = mouse.x - dot.baseX;
                const dy = mouse.y - dot.baseY;
                const dist = Math.sqrt(dx * dx + dy * dy);
                const maxDist = 180;

                let offsetX = 0;
                let offsetY = 0;
                if (dist < maxDist) {
                    const factor = (1 - dist / maxDist) * 10;
                    offsetX = -(dx / dist) * factor;
                    offsetY = -(dy / dist) * factor;
                }

                // Breathing pulse
                const pulse = Math.sin(time + dot.phase) * 0.5 + 0.5;
                const alpha = Math.max(0.03, baseAlpha * pulse * (1 - dot.baseY / height * 0.35));
                const size = 1.2 + pulse * 0.6;

                const x = dot.baseX + offsetX;
                const y = dot.baseY + offsetY;

                ctx.fillStyle = `rgba(${primaryColor}, ${alpha})`;
                ctx.beginPath();
                ctx.arc(x, y, size, 0, Math.PI * 2);
                ctx.fill();
            }

            requestAnimationFrame(animate);
        }

        requestAnimationFrame(animate);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initMatrixField);
    } else {
        initMatrixField();
    }
})();

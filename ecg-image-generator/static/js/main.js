document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('configForm');
    const generateBtn = document.getElementById('generateBtn');
    const btnText = generateBtn.querySelector('.btn-text');
    const spinner = generateBtn.querySelector('.spinner');
    
    const canvasContainer = document.getElementById('canvasContainer');
    const emptyState = canvasContainer.querySelector('.empty-state');
    const loadingState = canvasContainer.querySelector('.loading-state');
    const downloadBtn = document.getElementById('downloadBtn');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // UI Loading State
        generateBtn.disabled = true;
        btnText.textContent = 'Generating...';
        spinner.classList.remove('hidden');
        
        emptyState.classList.add('hidden');
        loadingState.classList.remove('hidden');
        
        // Remove old images if any
        const oldCards = canvasContainer.querySelectorAll('.generated-image-card');
        oldCards.forEach(card => card.remove());

        // Gather Data
        const formData = new FormData(form);
        const configData = {
            inputDir: formData.get('inputDir'),
            hwText: formData.get('hwText') === 'on',
            wrinkles: formData.get('wrinkles') === 'on',
            augment: formData.get('augment') === 'on',
            printHeader: formData.get('printHeader') === 'on',
            addQrCode: formData.get('addQrCode') === 'on',
            randomResolution: formData.get('randomResolution') === 'on',
            maskUnplotted: formData.get('maskUnplotted') === 'on'
        };

        try {
            const response = await fetch('/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(configData)
            });

            const result = await response.json();

            if (result.success && result.images.length > 0) {
                showToast('Generation completed successfully!', 'success');
                renderImages(result.images);
            } else {
                throw new Error(result.error || 'No images were generated.');
            }
        } catch (err) {
            console.error(err);
            showToast(err.message, 'error');
            emptyState.classList.remove('hidden');
        } finally {
            // Restore UI
            generateBtn.disabled = false;
            btnText.textContent = 'Generate Image';
            spinner.classList.add('hidden');
            loadingState.classList.add('hidden');
        }
    });

    function renderImages(imageUrls) {
        // Just show the first one for now in the main view
        imageUrls.forEach((url, i) => {
            const card = document.createElement('div');
            card.className = 'generated-image-card';
            card.style.display = i === 0 ? 'block' : 'none'; // Basic carousel logic could go here
            
            const img = document.createElement('img');
            // Adding timestamp to bypass cache
            img.src = `${url}?t=${new Date().getTime()}`;
            img.alt = 'Synthetic ECG Output';
            
            card.appendChild(img);
            canvasContainer.appendChild(card);
        });
    }

    function showToast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        let icon = '';
        if (type === 'success') icon = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><path d="M22 4L12 14.01l-3-3"/></svg>';
        else if (type === 'error') icon = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 8v4m0 4h.01"/></svg>';

        toast.innerHTML = `${icon} <span>${message}</span>`;
        container.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    }
});

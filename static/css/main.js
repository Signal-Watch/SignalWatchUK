// SignalWatch JavaScript functionality

// Toggle scan mode sections
document.addEventListener('DOMContentLoaded', function() {
    const scanModeRadios = document.querySelectorAll('input[name="scanMode"]');
    const specificSection = document.getElementById('specificSection');
    const filteredSection = document.getElementById('filteredSection');
    const companyNumbers = document.getElementById('companyNumbers');
    
    scanModeRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            if (this.value === 'specific') {
                specificSection.style.display = 'block';
                filteredSection.style.display = 'none';
                companyNumbers.required = true;
            } else {
                specificSection.style.display = 'none';
                filteredSection.style.display = 'block';
                companyNumbers.required = false;
            }
        });
    });
});

// Utility functions
const SignalWatch = {
    // Format date for display
    formatDate: function(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-GB');
    },
    
    // Format company number
    formatCompanyNumber: function(number) {
        return number.padStart(8, '0');
    },
    
    // Show notification
    showNotification: function(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 25px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            z-index: 10000;
            animation: slideIn 0.3s ease;
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    },
    
    // Copy to clipboard
    copyToClipboard: function(text) {
        navigator.clipboard.writeText(text).then(() => {
            this.showNotification('Copied to clipboard!', 'success');
        }).catch(err => {
            console.error('Failed to copy:', err);
        });
    },
    
    // Download data as file
    downloadData: function(data, filename, type = 'application/json') {
        const blob = new Blob([data], { type });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    }
};

// Add CSS for animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// Make available globally
window.SignalWatch = SignalWatch;

// DOM Elements
const imageInput = document.getElementById('imageInput');
const uploadArea = document.getElementById('uploadArea');
const imagePreview = document.getElementById('imagePreview');
const imagePreviewContainer = document.getElementById('imagePreviewContainer');
const removeImageBtn = document.getElementById('removeImageBtn');
const textInput = document.getElementById('textInput');
const analyzeBtn = document.getElementById('analyzeBtn');
const loadingOverlay = document.getElementById('loadingOverlay');
const resultsSection = document.getElementById('resultsSection');
const charCount = document.getElementById('charCount');

// Tab switching
document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const tab = btn.dataset.tab;
        document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
        document.getElementById(`${tab}Tab`).classList.add('active');
    });
});

// Image upload handling
uploadArea.addEventListener('click', () => imageInput.click());
uploadArea.addEventListener('dragover', (e) => { e.preventDefault(); uploadArea.style.borderColor = '#667eea'; });
uploadArea.addEventListener('dragleave', () => uploadArea.style.borderColor = '#e0e4e8');
uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) handleImageFile(file);
    uploadArea.style.borderColor = '#e0e4e8';
});

imageInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files[0]) handleImageFile(e.target.files[0]);
});

function handleImageFile(file) {
    const reader = new FileReader();
    reader.onload = (event) => {
        imagePreview.src = event.target.result;
        imagePreviewContainer.style.display = 'block';
        document.querySelector('.upload-card .upload-icon').style.display = 'none';
        document.querySelector('.upload-card h3').style.display = 'none';
        document.querySelector('.upload-card p').style.display = 'none';
        document.querySelector('.format-hint').style.display = 'none';
    };
    reader.readAsDataURL(file);
}

removeImageBtn.addEventListener('click', () => {
    imageInput.value = '';
    imagePreviewContainer.style.display = 'none';
    document.querySelector('.upload-card .upload-icon').style.display = 'block';
    document.querySelector('.upload-card h3').style.display = 'block';
    document.querySelector('.upload-card p').style.display = 'block';
    document.querySelector('.format-hint').style.display = 'block';
});

// Character counter
textInput.addEventListener('input', () => {
    charCount.textContent = textInput.value.length;
});

// Analyze function
analyzeBtn.addEventListener('click', async () => {
    const imageFile = imageInput.files[0];
    const text = textInput.value.trim();
    
    if (!imageFile && !text) {
        alert('Vui lòng cung cấp ảnh hoặc văn bản để phân tích');
        return;
    }
    
    // Show loading, hide results
    loadingOverlay.style.display = 'block';
    resultsSection.style.display = 'none';
    analyzeBtn.disabled = true;
    
    const formData = new FormData();
    if (imageFile) formData.append('image', imageFile);
    if (text) formData.append('text', text);
    
    try {
        const response = await fetch('http://127.0.0.1:5000/predictcombined', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const data = await response.json();
        displayResults(data);
        
    } catch (error) {
        console.error('Error:', error);
        alert('Lỗi kết nối đến server. Đảm bảo backend đang chạy tại port 5000');
    } finally {
        loadingOverlay.style.display = 'none';
        analyzeBtn.disabled = false;
    }
});

function displayResults(data) {
    // Show results section
    resultsSection.style.display = 'block';
    
    // Image analysis
    if (data.image_prediction && data.image_prediction !== 'No image provided') {
        document.getElementById('imageBadge').textContent = data.image_prediction;
        document.getElementById('imageBadge').className = `result-badge ${data.image_prediction === 'Authentic' ? 'authentic' : 'tampered'}`;
        document.getElementById('imageDetail').textContent = data.image_description || 
            (data.image_prediction === 'Authentic' ? 'Không phát hiện dấu hiệu chỉnh sửa' : 'Phát hiện dấu hiệu chỉnh sửa trong ảnh');
        
        // Show ELA image if available
        if (data.ela_image) {
            const elaImg = document.getElementById('resultElaImg');
            elaImg.src = `data:image/jpeg;base64,${data.ela_image}`;
            elaImg.style.display = 'block';
        }
    } else {
        document.getElementById('imageBadge').textContent = 'Không có ảnh';
        document.getElementById('imageBadge').className = 'result-badge';
        document.getElementById('imageDetail').textContent = 'Không có ảnh để phân tích';
    }
    
    // Show original image if uploaded
    if (imageInput.files[0]) {
        const reader = new FileReader();
        reader.onload = (e) => { document.getElementById('resultOriginalImg').src = e.target.result; };
        reader.readAsDataURL(imageInput.files[0]);
    }
    
    // Text analysis
    if (data.news_prediction && data.news_prediction !== 'No text provided') {
        document.getElementById('textBadge').textContent = data.news_prediction;
        document.getElementById('textBadge').className = `result-badge ${data.news_prediction === 'Real' ? 'real' : 'fake'}`;
        document.getElementById('textDetail').textContent = data.text_description ||(data.news_prediction === 'Real' ? 'Nội dung có độ tin cậy cao' : 'Nội dung có dấu hiệu tin giả');
        document.querySelector('.preview-content').textContent = textInput.value.substring(0, 300) + (textInput.value.length > 300 ? '...' : '');
    } else {
        document.getElementById('textBadge').textContent = 'Không có văn bản';
        document.getElementById('textBadge').className = 'result-badge';
        document.getElementById('textDetail').textContent = 'Không có văn bản để phân tích';
        document.querySelector('.preview-content').textContent = 'Chưa có văn bản...';
    }
    
    const heatmapImg = document.getElementById('resultHeatmapImg');
    console.log("Heatmap data:", data.heatmap_image ? "Có": "Không");
    if (data.heatmap_image) {
        heatmapImg.src = `data:image/jpeg;base64,${data.heatmap_image}`;
        heatmapImg.style.display = 'block';
    } else {
        heatmapImg.style.display = 'none';
    }

    // Final verdict
    const verdict = data.final_verdict || 'SUSPICIOUS';
    const verdictDisplay = document.getElementById('verdictDisplay');
    const verdictText = document.getElementById('verdictDisplay .verdict-text');
    
    verdictDisplay.className = `verdict-display ${verdict.toLowerCase()}`;
    if (verdict === 'REAL') {
        document.querySelector('.verdict-icon').textContent = '✅';
        document.querySelector('.verdict-text').textContent = 'TIN THẬT';
    } else if (verdict === 'FAKE') {
        document.querySelector('.verdict-icon').textContent = '⚠️';
        document.querySelector('.verdict-text').textContent = 'TIN GIẢ';
    } else {
        document.querySelector('.verdict-icon').textContent = '❓';
        document.querySelector('.verdict-text').textContent = 'CẦN XÁC MINH THÊM';
    }
    
    const confidence = data.confidence || 0.75;
    document.getElementById('confidenceFill').style.width = `${confidence * 100}%`;
    document.getElementById('confidenceValue').textContent = `${(confidence * 100).toFixed(1)}%`;
    document.getElementById('verdictReason').textContent = data.reason || 'Phân tích dựa trên cả nội dung văn bản và hình ảnh';
    
    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth' });
}

// FEEDBACK MANAGEMENT
// ID document trong Firestore (feedback collection)
const FEEDBACK_DOC_ID = "3nhfJY24NmV20dicGQ5Q";

// Biến lưu kết quả hiện tại
let currentResultData = null;

// Hàm cập nhật currentResultData khi có kết quả mới
function updateCurrentResult(data) {
    currentResultData = {
        news_prediction: data.news_prediction,
        image_prediction: data.image_prediction,
        final_verdict: data.final_verdict,
        confidence: data.confidence,
        timestamp: new Date().toISOString()
    };
}

// Hàm reset kết quả (xóa hiển thị)
function resetResults() {
    // Ẩn section kết quả
    const resultsSection = document.getElementById('resultsSection');
    if (resultsSection) {
        resultsSection.style.display = 'none';
    }
    
    // Reset các giá trị hiển thị
    document.getElementById('confidenceFill').style.width = '0%';
    document.getElementById('confidenceValue').textContent = '0%';
    document.getElementById('verdictReason').textContent = '--';
    
    // Reset badge
    const imageBadge = document.getElementById('imageBadge');
    const textBadge = document.getElementById('textBadge');
    if (imageBadge) {
        imageBadge.textContent = '--';
        imageBadge.className = 'result-badge';
    }
    if (textBadge) {
        textBadge.textContent = '--';
        textBadge.className = 'result-badge';
    }
    
    // Reset ảnh preview
    const resultOriginalImg = document.getElementById('resultOriginalImg');
    const resultElaImg = document.getElementById('resultElaImg');
    const resultHeatmapImg = document.getElementById('resultHeatmapImg');
    
    if (resultOriginalImg) resultOriginalImg.src = '';
    if (resultElaImg) {
        resultElaImg.src = '';
        resultElaImg.style.display = 'none';
    }
    if (resultHeatmapImg) {
        resultHeatmapImg.src = '';
        resultHeatmapImg.style.display = 'none';
    }
    
    // Reset text preview
    const previewContent = document.querySelector('.preview-content');
    if (previewContent) {
        previewContent.textContent = '--';
    }
    
    // Reset nội dung text input (tùy chọn)
    // document.getElementById('textInput').value = '';
    // document.getElementById('charCount').textContent = '0';
    
    // Reset file ảnh
    const imageInput = document.getElementById('imageInput');
    if (imageInput) imageInput.value = '';
    
    const imagePreviewContainer = document.getElementById('imagePreviewContainer');
    if (imagePreviewContainer) {
        imagePreviewContainer.style.display = 'none';
    }
    
    // Hiển thị lại upload area
    const uploadCard = document.querySelector('.upload-card');
    if (uploadCard) {
        const uploadIcon = uploadCard.querySelector('.upload-icon');
        const uploadTitle = uploadCard.querySelector('h3');
        const uploadText = uploadCard.querySelector('p');
        const formatHint = uploadCard.querySelector('.format-hint');
        if (uploadIcon) uploadIcon.style.display = 'block';
        if (uploadTitle) uploadTitle.style.display = 'block';
        if (uploadText) uploadText.style.display = 'block';
        if (formatHint) formatHint.style.display = 'block';
    }
    
    // Scroll lên đầu trang
    window.scrollTo({ top: 0, behavior: 'smooth' });
    
    // Xóa thông báo sau 3 giây
    setTimeout(() => {
        const msgDiv = document.getElementById('fbFeedbackMessage');
        if (msgDiv) msgDiv.textContent = '';
    }, 3000);
    
    console.log("🔄 Đã reset kết quả, sẵn sàng phân tích mới");
}
// Hàm lưu like/dislike lên Firebase và xóa kết quả
async function saveFeedbackAndReset(feedbackType, isCorrect) {
    if (!window.db || !window.firestoreHelpers) {
        console.log("⚠️ Firebase chưa sẵn sàng");
        // Vẫn cho reset kết quả
        resetResults();
        return;
    }
    
    try {
        const { doc, updateDoc, increment } = window.firestoreHelpers;
        const docRef = doc(window.db, 'feedback', FEEDBACK_DOC_ID);
        
        // Tăng số lượng like hoặc dislike
        if (feedbackType === 'like') {
            await updateDoc(docRef, {
                likes: increment(1)
            });
            console.log("✅ Đã tăng like");
        } else {
            await updateDoc(docRef, {
                dislikes: increment(1)
            });
            console.log("✅ Đã tăng dislike");
        }
        
        // Hiển thị thông báo
        const msgDiv = document.getElementById('fbFeedbackMessage');
        if (msgDiv) {
            if (feedbackType === 'like') {
                msgDiv.textContent = '✅ Cảm ơn bạn! Phản hồi đã được ghi nhận.';
                msgDiv.style.color = '#28a745';
            } else {
                msgDiv.textContent = '📝 Cảm ơn bạn! Chúng tôi sẽ cải thiện AI.';
                msgDiv.style.color = '#dc3545';
            }
        }
        
        // Lưu feedback vào localStorage để thống kê
        const feedbacks = JSON.parse(localStorage.getItem('fakeshield_feedbacks') || '{}');
        feedbacks[Date.now()] = {
            type: feedbackType,
            timestamp: new Date().toISOString(),
            result: currentResultData
        };
        localStorage.setItem('fakeshield_feedbacks', JSON.stringify(feedbacks));
        
        // Chờ 1.5 giây để người dùng thấy thông báo, rồi reset
        setTimeout(() => {
            resetResults();
        }, 1500);
        
    } catch (error) {
        console.error("❌ Firebase error:", error);
        // Vẫn reset kết quả dù Firebase lỗi
        resetResults();
    }
}

// Gán sự kiện cho nút Like/Dislike
function initFeedbackButtons() {
    const likeBtn = document.getElementById('fbLikeBtn');
    const dislikeBtn = document.getElementById('fbDislikeBtn');
    
    if (likeBtn) {
        // Xóa sự kiện cũ để tránh trùng lặp
        const newLikeBtn = likeBtn.cloneNode(true);
        likeBtn.parentNode.replaceChild(newLikeBtn, likeBtn);
        newLikeBtn.addEventListener('click', () => {
            if (currentResultData) {
                saveFeedbackAndReset('like', true);
            } else {
                alert('Chưa có kết quả nào để đánh giá!');
            }
        });
    }
    
    if (dislikeBtn) {
        const newDislikeBtn = dislikeBtn.cloneNode(true);
        dislikeBtn.parentNode.replaceChild(newDislikeBtn, dislikeBtn);
        newDislikeBtn.addEventListener('click', () => {
            if (currentResultData) {
                saveFeedbackAndReset('dislike', false);
            } else {
                alert('Chưa có kết quả nào để đánh giá!');
            }
        });
    }
}

// ========== HISTORY MANAGEMENT ==========
const STORAGE_KEY = 'fakeshield_history';
const MAX_HISTORY = 50;  // Giữ tối đa 50 kết quả

// Lưu kết quả vào lịch sử
function saveToHistory(result) {
    const history = getHistory();
    
    const historyItem = {
        id: Date.now(),
        timestamp: new Date().toLocaleString('vi-VN'),
        verdict: result.final_verdict,
        confidence: result.confidence,
        reason: result.reason,
        news_prediction: result.news_prediction,
        image_prediction: result.image_prediction,
        text_preview: textInput.value?.substring(0, 100) || 'Không có văn bản',
        hasImage: !!imageInput.files[0]
    };
    
    history.unshift(historyItem);
    
    // Giới hạn số lượng
    if (history.length > MAX_HISTORY) history.pop();
    
    localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
    renderHistory();
}

// Lấy lịch sử từ localStorage
function getHistory() {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? JSON.parse(stored) : [];
}

// Xóa toàn bộ lịch sử
function clearHistory() {
    if (confirm('Bạn có chắc muốn xóa toàn bộ lịch sử phân tích?')) {
        localStorage.removeItem(STORAGE_KEY);
        renderHistory();
    }
}

// Xóa một mục lịch sử
function deleteHistoryItem(id) {
    const history = getHistory();
    const newHistory = history.filter(item => item.id !== id);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(newHistory));
    renderHistory();
}

// Hiển thị lịch sử
function renderHistory() {
    const historyList = document.getElementById('historyList');
    const history = getHistory();
    
    if (!historyList) return;
    
    if (history.length === 0) {
        historyList.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📋</div>
                <h3>Chưa có lịch sử phân tích</h3>
                <p>Hãy phân tích một bài viết hoặc ảnh để lưu lại kết quả</p>
            </div>
        `;
        return;
    }
    
    historyList.innerHTML = history.map(item => `
        <div class="history-item ${item.verdict.toLowerCase()}" data-id="${item.id}">
            <div class="history-header-row">
                <span class="history-verdict ${item.verdict.toLowerCase()}">
                    ${item.verdict === 'REAL' ? '✅ TIN THẬT' : item.verdict === 'FAKE' ? '⚠️ TIN GIẢ' : '❓ CẦN XÁC MINH'}
                </span>
                <div>
                    <span class="history-time">🕐 ${item.timestamp}</span>
                    <button class="delete-history-btn" data-id="${item.id}" title="Xóa">🗑️</button>
                </div>
            </div>
            <div class="history-preview">
                📝 ${item.text_preview}${item.text_preview.length === 100 ? '...' : ''}
            </div>
            <div class="history-details">
            <span>🔍 Độ tin cậy: ${(item.confidence * 100).toFixed(1)}%</span>
                ${item.hasImage ? '<span>🖼️ Có ảnh</span>' : ''}
                ${item.news_prediction && item.news_prediction !== 'No text provided' ? `<span>📄 ${item.news_prediction}</span>` : ''}
                ${item.image_prediction && item.image_prediction !== 'No image provided' ? `<span>🖼️ ${item.image_prediction}</span>` : ''}
            </div>
        </div>
    `).join('');
    
    // Gán sự kiện xóa cho từng nút
    document.querySelectorAll('.delete-history-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const id = parseInt(btn.dataset.id);
            deleteHistoryItem(id);
        });
    });
    
    // Gán sự kiện click vào history item để load lại
    document.querySelectorAll('.history-item').forEach(item => {
        item.addEventListener('click', () => {
            // Có thể thêm chức năng load lại kết quả cũ
            console.log('Load history item:', item.dataset.id);
        });
    });
}

// Gọi renderHistory khi load trang
document.addEventListener('DOMContentLoaded', () => {
    renderHistory();
});

// Cập nhật hàm displayResults để lưu
const originalDisplayResults = displayResults;
window.displayResults = function(data) {
    // Lưu kết quả hiện tại
    updateCurrentResult(data);
    
    // Gọi hàm hiển thị gốc
    originalDisplayResults(data);
    
    saveToHistory(data)

    // Khởi tạo lại buttons (vì DOM có thể thay đổi)
    initFeedbackButtons();
};

// Gán sự kiện cho nút xóa lịch sử
const clearHistoryBtn = document.getElementById('clearHistoryBtn');
if (clearHistoryBtn) {
    clearHistoryBtn.addEventListener('click', clearHistory);
}


let verdictChartInstance = null;
let timelineChartInstance = null;

function renderStats() {
    const history = getHistory();
    if (history.length === 0) return;

    const verdictCounts = {
        'REAL' : history.filter(h => h.verdict === 'REAL').length,
        'FAKE' : history.filter(h => h.verdict === 'FAKE').length,
        'SUSPICIOUS' : history.filter(h => h.verdict === 'SUSPICIOUS').length,
    };

    if (verdictChartInstance) verdictChartInstance.destroy(); // Hủy chart cũ nếu đã tồn tại

    const ctx = document.getElementById('verdictChart').getContext('2d');
    new Chart(ctx, {
        type: 'pie',
        data: {
            labels: ['✅ Tin Thật', '⚠️ Tin giả', '❓ Cần xác minh'],
            datasets: [{
                data: [verdictCounts.REAL, verdictCounts.FAKE, verdictCounts.SUSPICIOUS],
                backgroundColor: ['#28a745', '#dc3545', '#ffc107'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'bottom' },
            }
        }
    });

    const last7Days = getlast7DaysStats(history);

    if (timelineChartInstance) timelineChartInstance.destroy(); // Hủy chart cũ nếu đã tồn tại

    const timelineCtx = document.getElementById('timelineChart').getContext('2d');
    new Chart(timelineCtx, {
        type: 'line',
        data: {
            labels: last7Days.labels,
            datasets: [
                {label: 'Tin Thật', data: last7Days.REAL, borderColor: '#28a745', tension: 0.3},
                {label: 'Tin Giả', data: last7Days.FAKE, borderColor: '#dc3545', tension: 0.3},
            ]
        },
        options: {responsive: true}
    });
}

function getlast7DaysStats(history){
    const labels = [];
    const real = [];
    const fake = [];

    for (let i = 6; i >=0; i--) {
        const date = new Date();
        date.setDate(date.getDate() - i);
        const dateStr = date.toLocaleDateString('vi-VN');
        labels.push(dateStr);

        const dayHistory = history.filter(h => {
            const hDate = new Date(h.timestamp.split(',')[0]);
            return hDate.toDateString() === date.toDateString();
        });

        real.push(dayHistory.filter(h => h.verdict === 'REAL').length);
        fake.push(dayHistory.filter(h => h.verdict === 'FAKE').length);
    }

    return { labels, real, fake };
}

document.querySelector('[data-tab="history"]').addEventListener('click', () => {
    setTimeout(renderStats, 100);
});

// ========== URL ANALYSIS ==========
const urlInput = document.getElementById('urlInput');
const analyzeUrlBtn = document.getElementById('analyzeUrlBtn');
const urlResult = document.getElementById('urlResult');
const urlResultContent = document.getElementById('urlResultContent');

if (analyzeUrlBtn) {
    analyzeUrlBtn.addEventListener('click', async () => {
        const url = urlInput.value.trim();
        
        if (!url) {
            alert('Vui lòng nhập link bài báo');
            return;
        }
        
        // Kiểm tra URL hợp lệ
        if (!url.startsWith('http://') && !url.startsWith('https://')) {
            alert('Vui lòng nhập link bắt đầu bằng http:// hoặc https://');
            return;
        }
        
        urlResult.style.display = 'block';
        urlResultContent.innerHTML = '<div class="loading-spinner">🔄 Đang phân tích link...</div>';
        analyzeUrlBtn.disabled = true;
        analyzeUrlBtn.textContent = '⏳ Đang xử lý...';
        
        try {
            const formData = new FormData();
            formData.append('url', url);
            
            const response = await fetch('http://127.0.0.1:5000/predicturl', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Lỗi server');
            }
            
            const data = await response.json();
            
            // Xác định class cho badge
            let badgeClass = 'suspicious';
            let badgeText = '❓ CẦN XÁC MINH';
            if (data.final_verdict === 'REAL') {
                badgeClass = 'real';
                badgeText = '✅ TIN THẬT';
            } else if (data.final_verdict === 'FAKE') {
                badgeClass = 'fake';
                badgeText = '⚠️ TIN GIẢ';
            }
            
            urlResultContent.innerHTML = `
                <div class="url-result-card">
                    <h5>📰 ${escapeHtml(data.title) || 'Không có tiêu đề'}</h5>
                    <p><strong>🔍 Kết quả:</strong> 
                        <span class="badge ${badgeClass}">${badgeText}</span>
                    </p>
                    <p><strong>📝 Văn bản:</strong> ${data.news_prediction || 'Không xác định'}</p>
                    <p><strong>🖼️ Hình ảnh:</strong> ${data.image_prediction || 'Không có ảnh'}</p>
                    <p><strong>🎯 Độ tin cậy:</strong> ${(data.confidence * 100).toFixed(1)}%</p>
                    ${data.top_image ? `<img src="${data.top_image}" style="max-width: 100%; max-height: 200px; border-radius: 8px; margin-top: 10px;" onerror="this.style.display='none'">` : ''}
                    <details>
                        <summary style="cursor: pointer; margin-top: 10px;">📖 Xem nội dung trích xuất</summary>
                        <div class="text-preview">${escapeHtml(data.text_preview || 'Không có nội dung')}</div>
                    </details>
                </div>
            `;
            
        } catch (error) {
            console.error('Lỗi:', error);
            urlResultContent.innerHTML = `<div style="color: #dc3545; padding: 20px; text-align: center;">
                ❌ Lỗi: ${error.message}<br>
                <small>Vui lòng thử lại hoặc kiểm tra link</small>
            </div>`;
        } finally {
            analyzeUrlBtn.disabled = false;
            analyzeUrlBtn.textContent = '📰 Phân tích link';
        }
    });
}

// Hàm escapeHtml để tránh XSS
function escapeHtml(str) {
    if (!str) return '';
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// Khởi tạo khi trang load
document.addEventListener('DOMContentLoaded', () => {
    renderHistory();
    initFeedbackButtons();
});
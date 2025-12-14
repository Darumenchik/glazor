let currentUser = null;

// Инициализация
window.onload = () => {
    const saved = localStorage.getItem('glazor_user');
    if (saved) {
        try {
            currentUser = JSON.parse(saved);
            showApp();
            loadFeed();
        } catch (e) {
            localStorage.removeItem('glazor_user');
            location.reload();
        }
    }
};

// --- НАВИГАЦИЯ ---
function toggleAuth(type) {
    document.getElementById('login-form').classList.toggle('hidden', type !== 'login');
    document.getElementById('register-form').classList.toggle('hidden', type !== 'register');
}
function showRegister() { toggleAuth('register'); }
function showLogin() { toggleAuth('login'); }

function showApp() {
    document.getElementById('auth-container').classList.add('hidden');
    document.getElementById('app').classList.remove('hidden');
    if (currentUser) {
        document.getElementById('username').textContent = currentUser.name;
        document.getElementById('user-avatar').src = currentUser.avatar || 'https://i.ibb.co/0jQjZfV/default-avatar.jpg';
    }
}

function logout() {
    localStorage.removeItem('glazor_user');
    currentUser = null;
    location.reload();
}

// --- УТИЛИТА ЗАГРУЗКИ КНОПОК ---
function setLoading(btn, isLoading, loadingText = 'Ждём...') {
    if (!btn) return;
    
    if (isLoading) {
        btn.dataset.text = btn.innerText;
        btn.innerText = loadingText;
        btn.disabled = true;
    } else {
        btn.innerText = btn.dataset.text || 'Кнопка';
        btn.disabled = false;
    }
}

// --- API ЗАПРОСЫ ---
async function register() {
    const btn = document.querySelector('#register-form button');
    if (!btn) return;
    
    setLoading(btn, true, 'Регистрируем...');

    const name = document.getElementById('reg-name').value.trim();
    const phone = document.getElementById('reg-phone').value.trim();
    const password = document.getElementById('reg-password').value;
    const avatar = document.getElementById('reg-avatar').files[0];

    if (!name || !phone || !password) {
        alert('Заполни все поля');
        setLoading(btn, false);
        return;
    }

    // Создаем FormData
    const formData = new FormData();
    formData.append('name', name);
    formData.append('phone', phone);
    formData.append('password', password);
    if (avatar) {
        formData.append('avatar', avatar);
    }

    try {
        const res = await fetch('/api/register', { 
            method: 'POST', 
            body: formData
        });
        
        const data = await res.json();
        
        if (data.success) {
            alert('✅ Аккаунт создан!');
            
            // Автоматически входим после регистрации
            if (data.user) {
                currentUser = data.user;
                localStorage.setItem('glazor_user', JSON.stringify(currentUser));
                showApp();
                loadFeed();
            } else {
                showLogin();
            }
            
            // Очищаем форму
            document.getElementById('reg-name').value = '';
            document.getElementById('reg-phone').value = '';
            document.getElementById('reg-password').value = '';
            document.getElementById('reg-avatar').value = '';
        } else {
            alert(data.message || 'Ошибка регистрации');
        }

    } catch (e) { 
        alert('Ошибка сети. Проверь сервер.'); 
        console.error(e);
    } finally {
        setLoading(btn, false); 
    }
}

// ФУНКЦИЯ LOGIN
async function login() {
    const btn = document.querySelector('#login-form button');
    if (!btn) return;
    
    setLoading(btn, true, 'Проверяем...');

    const phone = document.getElementById('login-phone').value.trim();
    const password = document.getElementById('login-password').value;

    if (!phone || !password) {
        alert('Введите телефон и пароль');
        setLoading(btn, false);
        return;
    }

    try {
        const res = await fetch('/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ phone, password })
        });
        
        let data = {};
        try {
            data = await res.json();
        } catch (e) {
            alert('Ошибка сервера');
            setLoading(btn, false);
            return;
        }

        if (res.ok && data.user) {
            currentUser = data.user;
            localStorage.setItem('glazor_user', JSON.stringify(currentUser));
            showApp();
            loadFeed();
            // Очищаем форму
            document.getElementById('login-phone').value = '';
            document.getElementById('login-password').value = '';
        } else {
            alert(data.message || 'Неверные данные');
        }

    } catch (e) { 
        alert('Ошибка сети. Проверь, запущен ли сервер.'); 
        console.error(e);
    } finally {
        setLoading(btn, false);
    }
}

async function uploadPost() {
    const btn = document.querySelector('.post-form button');
    const fileInput = document.getElementById('photo');
    const file = fileInput.files[0];
    
    if (!file) {
        alert('Сначала выбери фото!');
        return;
    }
    
    if (!currentUser) {
        alert('Сначала войдите в аккаунт');
        return;
    }
    
    setLoading(btn, true, 'Публикуем...');

    const formData = new FormData();
    formData.append('photo', file);
    formData.append('userId', currentUser.id);

    try {
        const res = await fetch('/api/posts', { 
            method: 'POST', 
            body: formData 
        });
        
        if (res.ok) {
            fileInput.value = '';
            await loadFeed();
            alert('Пост опубликован!');
        } else {
            const data = await res.json();
            alert(data.message || 'Ошибка загрузки поста');
        }
    } catch(e) { 
        alert('Ошибка сети при публикации'); 
        console.error(e);
    }
    
    setLoading(btn, false);
}

// --- ЛЕНТА И ЛАЙКИ ---
async function loadFeed() {
    if (!currentUser) return;

    const feed = document.getElementById('feed');
    if (!feed) return;

    try {
        const res = await fetch('/api/posts');
        const posts = await res.json();

        feed.innerHTML = '';

        if (!posts || posts.length === 0) {
            feed.innerHTML = '<div style="text-align:center; padding:40px; color:#888">Пока нет постов. Будь первым!</div>';
            return;
        }

        // Сортируем посты: новые сверху
        posts.slice().reverse().forEach(post => {
            const likedBy = post.likedBy || [];
            const isLiked = likedBy.includes(currentUser.id);
            const heartClass = isLiked ? 'fas fa-heart liked' : 'far fa-heart';
            const comments = post.comments || [];

            const div = document.createElement('div');
            div.className = 'post';
            div.innerHTML = `
                <div class="post-header">
                    <img src="${post.userAvatar || 'https://i.ibb.co/0jQjZfV/default-avatar.jpg'}" 
                         class="post-avatar" 
                         onerror="this.src='https://i.ibb.co/0jQjZfV/default-avatar.jpg'">
                    <strong>${post.userName || 'Аноним'}</strong>
                </div>
                <img src="${post.photoUrl}" 
                     class="post-image"
                     ondblclick="handleLike('${post.id}')"
                     onerror="this.src='https://i.ibb.co/0jQjZfV/default-avatar.jpg'">
                <div class="actions">
                    <div onclick="handleLike('${post.id}')" style="cursor:pointer; display:flex; align-items:center; gap:8px;">
                        <i class="${heartClass}" id="icon-${post.id}"></i>
                        <span id="likes-${post.id}">${post.likes || 0}</span>
                    </div>
                </div>
                <div class="comments">
                    ${renderComments(comments)}
                </div>
                <div class="comment-form" style="margin-top:10px;">
                    <input type="text" id="input-${post.id}" placeholder="Добавить комментарий...">
                    <button onclick="sendComment('${post.id}')" style="padding:8px 16px;">Отправить</button>
                </div>
            `;
            feed.appendChild(div);
        });

    } catch (e) {
        console.error('Ошибка загрузки ленты:', e);
        feed.innerHTML = '<div style="text-align:center; padding:40px; color:#ff5555">Ошибка загрузки ленты</div>';
    }
}

function renderComments(comments) {
    if (!comments || comments.length === 0) {
        return '<div style="color:#888; padding:10px 0;">Пока нет комментариев</div>';
    }
    
    return comments.map(c => `
        <div class="comment-row">
            <span class="comment-author">${c.name || 'Аноним'}:</span>
            <span>${c.text || ''}</span>
        </div>
    `).join('');
}

async function handleLike(postId) {
    if (!currentUser) {
        alert('Войдите, чтобы ставить лайки');
        return;
    }

    const icon = document.getElementById(`icon-${postId}`);
    const countSpan = document.getElementById(`likes-${postId}`);
    
    if (!icon || !countSpan) return;

    let currentLikes = parseInt(countSpan.innerText) || 0;
    let isLiked = icon.classList.contains('liked');

    // Оптимистичное обновление
    if (isLiked) {
        icon.className = 'far fa-heart';
        countSpan.innerText = currentLikes - 1;
    } else {
        icon.className = 'fas fa-heart liked';
        countSpan.innerText = currentLikes + 1;
        icon.style.animation = 'none';
        void icon.offsetWidth;
        icon.style.animation = 'pulse 0.4s ease-in-out';
    }

    // Запрос на сервер
    try {
        const res = await fetch(`/api/posts/${postId}/like`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ userId: currentUser.id })
        });
        
        if (!res.ok) {
            throw new Error('Ошибка сервера');
        }

    } catch(e) {
        // Откат если ошибка
        alert('Ошибка при отправке лайка');
        icon.className = isLiked ? 'fas fa-heart liked' : 'far fa-heart';
        countSpan.innerText = currentLikes;
    }
}

async function sendComment(postId) {
    if (!currentUser) {
        alert('Войдите, чтобы комментировать');
        return;
    }

    const input = document.getElementById(`input-${postId}`);
    const text = input.value.trim();
    
    if (!text) {
        alert('Введите текст комментария');
        return;
    }

    try {
        const res = await fetch(`/api/posts/${postId}/comment`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                userId: currentUser.id, 
                text: text 
            })
        });
        
        if (res.ok) {
            input.value = '';
            await loadFeed(); // Перезагружаем ленту
        } else {
            const data = await res.json();
            alert(data.message || 'Не удалось отправить комментарий.');
        }
    } catch (e) {
        alert('Ошибка сети при отправке комментария.');
        console.error(e);
    }
}
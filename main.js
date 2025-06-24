function formatUAH(amount) {
    return (amount / 100).toLocaleString('uk-UA', {style: 'currency', currency: 'UAH', minimumFractionDigits: 2});
}

function renderDonateButtons(jarId, prefix) {
    if (!jarId) return;
    const amounts = [20, 40, 100];
    const container = document.getElementById(`${prefix}-donate`);
    container.innerHTML = amounts.map(amount =>
        `<a class="btn btn-success donate-btn" href="https://send.monobank.ua/jar/${jarId}?amount=${amount}" target="_blank" rel="noopener noreferrer">${amount} грн</a>`
    ).join("");
}

function renderJar(jarData, prefix) {
    document.getElementById(prefix + '-avatar').src = jarData.ownerIcon || 'https://placehold.co/64x64?text=?';
    document.getElementById(prefix + '-title').innerText = jarData.title || 'Без назви';
    document.getElementById(prefix + '-owner').innerText = jarData.ownerName || '';
    document.getElementById(prefix + '-balance').innerText = (jarData.amount !== undefined)
        ? formatUAH(jarData.amount)
        : 'Немає даних';
    renderDonateButtons(jarData.jarId, prefix);
}

function renderUpdatedAt(updated_at) {
    if (!updated_at) return;
    let el = document.getElementById('updated-at');
    if (!el) {
        el = document.createElement('div');
        el.id = 'updated-at';
        el.className = "text-center mt-3 text-muted";
        document.body.appendChild(el);
    }
    el.innerText = "Останнє оновлення: " + new Date(updated_at).toLocaleString('uk-UA');
}

async function updateJars() {
    try {
        const response = await fetch('balances.json', {cache: 'no-store'});
        if (!response.ok) throw new Error('balances.json не знайдено');
        const data = await response.json();
        if (Array.isArray(data.jars)) {
            if (data.jars[0]) renderJar(data.jars[0], 'jar1');
            if (data.jars[1]) renderJar(data.jars[1], 'jar2');
        }
        renderUpdatedAt(data.updated_at);
    } catch (e) {
        document.getElementById('jar1-title').innerText = 'Помилка';
        document.getElementById('jar1-balance').innerText = e.message;
        document.getElementById('jar2-title').innerText = 'Помилка';
        document.getElementById('jar2-balance').innerText = e.message;
    }
}

async function updateBestBidders() {
    try {
        const response = await fetch('best_bidders.json', {cache: 'no-store'});
        if (!response.ok) throw new Error('best_bidders.json не знайдено');
        const data = await response.json();
        // Для хлопчика (ліва банка)
        if (data.boy && data.boy.number !== undefined && data.boy.sum !== undefined) {
            document.getElementById('jar1-best').innerHTML =
                `<span class="fw-bold">Найбільша ставка:</span> Учасник №${data.boy.number}, ${data.boy.sum} грн`;
        }
        // Для дівчинки (права банка)
        if (data.girl && data.girl.number !== undefined && data.girl.sum !== undefined) {
            document.getElementById('jar2-best').innerHTML =
                `<span class="fw-bold">Найбільша ставка:</span> Учасник №${data.girl.number}, ${data.girl.sum} грн`;
        }
    } catch (e) {
        document.getElementById('jar1-best').innerText = '';
        document.getElementById('jar2-best').innerText = '';
    }
}

// Ініціалізуємо всі tooltip-и bootstrap
document.addEventListener('DOMContentLoaded', function() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.forEach(function (tooltipTriggerEl) {
        new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Викликати при старті і періодично
    updateJars();
    updateBestBidders();

    setInterval(updateJars, 60000);
    setInterval(updateBestBidders, 60000);
});

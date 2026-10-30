document.querySelectorAll('form[data-confirm]').forEach(form => {
  form.addEventListener('submit', event => {
    if (!window.confirm(form.dataset.confirm || 'Подтвердить действие?')) event.preventDefault();
  });
});

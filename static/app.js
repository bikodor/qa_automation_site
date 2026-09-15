const dialog = document.querySelector('#delete-dialog');
document.querySelector('#open-delete')?.addEventListener('click', () => dialog.showModal());
document.querySelector('#cancel-delete')?.addEventListener('click', () => dialog.close());

document.getElementById('uploadForm').addEventListener('submit', async (event) => {
    event.preventDefault();

    const formData = new FormData();
    formData.append('title', document.getElementById('title').value);
    formData.append('description', document.getElementById('description').value);
    formData.append('file', document.getElementById('file').files[0]);

    const response = await fetch('/upload', {
        method: 'POST',
        body: formData,
    });

    if (response.ok) {
        alert('File uploaded successfully!');
        loadImages();
    } else {
        alert('Failed to upload file.');
    }
});

async function loadImages() {
    const response = await fetch('/images');
    if (!response.ok) {
        alert('Failed to load images.');
        return;
    }

    const images = await response.json();
    const imageList = document.getElementById('imageList');
    imageList.innerHTML = ''; // 画像リストをクリア
    images.forEach(image => {
        const img = document.createElement('img');
        img.src = image.file_path; // S3のURLを使用
        img.alt = image.title; // 画像のタイトルをalt属性に設定
        const caption = document.createElement('p');
        caption.innerText = `${image.title}: ${image.description}`;
        const container = document.createElement('div');
        container.appendChild(img);
        container.appendChild(caption);
        imageList.appendChild(container);
    });
}

loadImages();


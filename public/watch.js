const video = document.getElementById('presentation');
const chapters = [...document.querySelectorAll('.chapters button[data-time]')];

for (const chapter of chapters) {
  chapter.addEventListener('click', () => {
    video.currentTime = Number(chapter.dataset.time);
    video.focus();
  });
}

function updateChapter() {
  const current = [...chapters].reverse().find(
    chapter => video.currentTime >= Number(chapter.dataset.time),
  );
  for (const chapter of chapters) {
    chapter.setAttribute('aria-current', chapter === current ? 'true' : 'false');
  }
}

video.addEventListener('timeupdate', updateChapter);
video.addEventListener('seeked', updateChapter);
updateChapter();

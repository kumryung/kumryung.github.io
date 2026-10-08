document.documentElement.classList.add("js");
const menuButton = document.querySelector(".menu-toggle");
const navigation = document.querySelector("#primary-nav");
function closeMenu(returnFocus = false) {
  menuButton.setAttribute("aria-expanded", "false");
  menuButton.setAttribute("aria-label", "메뉴 열기");
  navigation.classList.remove("is-open");
  if (returnFocus) menuButton.focus();
}
menuButton.addEventListener("click", () => {
  const open = menuButton.getAttribute("aria-expanded") !== "true";
  menuButton.setAttribute("aria-expanded", String(open));
  menuButton.setAttribute("aria-label", open ? "메뉴 닫기" : "메뉴 열기");
  navigation.classList.toggle("is-open", open);
});
navigation.addEventListener("click", (event) => {
  if (event.target.closest("a")) closeMenu();
});
document.addEventListener("keydown", (event) => {
  if (
    event.key === "Escape" &&
    menuButton.getAttribute("aria-expanded") === "true"
  )
    closeMenu(true);
});
document.addEventListener("click", (event) => {
  if (!event.target.closest(".site-header")) closeMenu();
});
window
  .matchMedia("(min-width: 761px)")
  .addEventListener("change", () => closeMenu());
document.querySelector("#year").textContent = new Date().getFullYear();
const copyButton = document.querySelector(".copy-email");
const copyStatus = document.querySelector(".copy-status");
if (navigator.clipboard && window.isSecureContext) {
  copyButton.hidden = false;
  copyButton.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText("ryan@ryanfamily.xyz");
      copyStatus.textContent = "이메일 주소를 복사했습니다.";
    } catch {
      copyStatus.textContent = "주소를 직접 선택해 복사해 주세요.";
    }
  });
}

const imageViewer = document.querySelector(".image-viewer");
const screenLinks = Array.from(document.querySelectorAll(".screen-link"));
const viewerImage = imageViewer.querySelector(".viewer-image");
const viewerTitle = imageViewer.querySelector("#viewer-title");
const viewerPosition = imageViewer.querySelector(".viewer-position");
let currentGallery = [];
let currentScreen = 0;
let screenOpener;

function showScreen(index) {
  currentScreen = (index + currentGallery.length) % currentGallery.length;
  const link = currentGallery[currentScreen];
  viewerImage.src = link.href;
  viewerImage.alt = link.querySelector("img").alt;
  viewerTitle.textContent = link.dataset.caption;
  viewerPosition.textContent = `${currentScreen + 1} / ${currentGallery.length}`;
}

if (typeof imageViewer.showModal === "function") {
  screenLinks.forEach((link) => {
    link.addEventListener("click", (event) => {
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey)
        return;
      event.preventDefault();
      screenOpener = link;
      currentGallery = screenLinks.filter(
        (item) => item.dataset.gallery === link.dataset.gallery,
      );
      showScreen(currentGallery.indexOf(link));
      imageViewer.showModal();
      document.body.classList.add("viewer-open");
    });
  });
}
imageViewer
  .querySelector(".viewer-close")
  .addEventListener("click", () => imageViewer.close());
imageViewer
  .querySelector(".viewer-previous")
  .addEventListener("click", () => showScreen(currentScreen - 1));
imageViewer
  .querySelector(".viewer-next")
  .addEventListener("click", () => showScreen(currentScreen + 1));
imageViewer.addEventListener("keydown", (event) => {
  if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
    event.preventDefault();
    showScreen(currentScreen + (event.key === "ArrowRight" ? 1 : -1));
  }
});
imageViewer.addEventListener("click", (event) => {
  const bounds = imageViewer.getBoundingClientRect();
  if (
    event.target === imageViewer &&
    (event.clientX < bounds.left ||
      event.clientX > bounds.right ||
      event.clientY < bounds.top ||
      event.clientY > bounds.bottom)
  )
    imageViewer.close();
});
imageViewer.addEventListener("close", () => {
  document.body.classList.remove("viewer-open");
  screenOpener?.focus({ preventScroll: true });
});

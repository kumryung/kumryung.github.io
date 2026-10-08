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

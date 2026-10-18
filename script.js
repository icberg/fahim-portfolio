// 1. Dynamic Footer Year
document.getElementById("year").textContent = new Date().getFullYear();

// 2. Theme Toggle (Light / Dark with localStorage + OS Preference fallback)
const rootEl = document.documentElement;
const themeToggle = document.getElementById("themeToggle");
const savedTheme = localStorage.getItem("fm-theme");
const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;

if (savedTheme) {
  rootEl.setAttribute("data-theme", savedTheme);
} else if (prefersDark) {
  rootEl.setAttribute("data-theme", "dark");
}

themeToggle.addEventListener("click", () => {
  const currentTheme = rootEl.getAttribute("data-theme");
  const nextTheme = currentTheme === "dark" ? "light" : "dark";
  rootEl.setAttribute("data-theme", nextTheme);
  localStorage.setItem("fm-theme", nextTheme);
});

// 3. Mobile Navigation Drawer
const navToggle = document.getElementById("navToggle");
const navLinks = document.getElementById("navLinks");

navToggle.addEventListener("click", () => {
  const isOpen = navLinks.classList.toggle("open");
  navToggle.setAttribute("aria-expanded", String(isOpen));
});

navLinks.querySelectorAll("a").forEach((link) => {
  link.addEventListener("click", () => {
    navLinks.classList.remove("open");
    navToggle.setAttribute("aria-expanded", "false");
  });
});

// 4. Scroll Progress Bar & Active Section Spy
const scrollProgress = document.getElementById("scrollProgress");
const sections = document.querySelectorAll("main section[id]");
const navItems = document.querySelectorAll(".nav-links a");

window.addEventListener("scroll", () => {
  const scrollTop = window.scrollY;
  const docHeight = document.documentElement.scrollHeight - window.innerHeight;
  const progress = docHeight > 0 ? (scrollTop / docHeight) * 100 : 0;
  scrollProgress.style.width = `${progress}%`;

  let currentSectionId = "";
  sections.forEach((sec) => {
    const top = sec.offsetTop - 140;
    if (scrollTop >= top) {
      currentSectionId = sec.getAttribute("id");
    }
  });

  navItems.forEach((link) => {
    link.classList.toggle(
      "active",
      link.getAttribute("href") === `#${currentSectionId}`
    );
  });
}, { passive: true });

// 5. Interactive Project Category Filter
const filterBtns = document.querySelectorAll(".filter-btn");
const projects = document.querySelectorAll("#projectGrid .project");

filterBtns.forEach((btn) => {
  btn.addEventListener("click", () => {
    filterBtns.forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");

    const filter = btn.getAttribute("data-filter");
    projects.forEach((card) => {
      if (filter === "all") {
        card.classList.remove("hidden-card");
      } else {
        const categories = (card.getAttribute("data-category") || "").split(" ");
        card.classList.toggle("hidden-card", !categories.includes(filter));
      }
    });
  });
});

// 6. Full-Resolution Image Lightbox Modal
const lightbox = document.getElementById("lightbox");
const lightboxImg = document.getElementById("lightboxImg");
const lightboxCaption = document.getElementById("lightboxCaption");
const lightboxClose = document.getElementById("lightboxClose");

document.querySelectorAll(".lightbox-trigger").forEach((img) => {
  img.addEventListener("click", () => {
    lightboxImg.src = img.src;
    lightboxImg.alt = img.alt;
    lightboxCaption.textContent = img.alt;
    lightbox.hidden = false;
    document.body.style.overflow = "hidden";
  });
});

function closeLightbox() {
  lightbox.hidden = true;
  lightboxImg.src = "";
  document.body.style.overflow = "";
}

lightboxClose.addEventListener("click", closeLightbox);
lightbox.addEventListener("click", (e) => {
  if (e.target === lightbox) closeLightbox();
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !lightbox.hidden) closeLightbox();
});

// 7. IntersectionObserver Reveal Animation
const revealEls = document.querySelectorAll(".reveal");
const observer = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("in-view");
        observer.unobserve(entry.target);
      }
    });
  },
  { threshold: 0.1 }
);
revealEls.forEach((el) => observer.observe(el));
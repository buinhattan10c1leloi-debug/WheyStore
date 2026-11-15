/**
 * WheyStore - Official GSAP 3.12+ Animations & Interactive E-Commerce Engine
 * Built following .agent/skills/ (gsap-core, gsap-timeline, gsap-scrolltrigger, gsap-plugins, gsap-performance, gsap-utils)
 * Color Palette: Matte Black (#222222) | Crimson Red (#D33F49) | Bright White (#F4F4F4)
 */

document.addEventListener("DOMContentLoaded", () => {
    if (typeof gsap === "undefined") return;

    // Register GSAP Plugins once at top level
    if (typeof ScrollTrigger !== "undefined") {
        gsap.registerPlugin(ScrollTrigger);
    }
    if (typeof Flip !== "undefined") {
        gsap.registerPlugin(Flip);
    }
    if (typeof TextPlugin !== "undefined") {
        gsap.registerPlugin(TextPlugin);
    }

    const cartBtn = document.getElementById("header-cart-btn");
    const cartBadge = document.getElementById("header-cart-badge");

    /**
     * Energetic Cart Badge Bounce (scale 1.25 -> 1 with elastic.out(1, 0.4))
     */
    function bounceCartBadge() {
        const targets = [cartBtn, cartBadge].filter(Boolean);
        if (!targets.length) return;

        gsap.fromTo(
            targets,
            { scale: 1.25 },
            {
                scale: 1,
                duration: 0.9,
                ease: "elastic.out(1, 0.4)",
                overwrite: "auto"
            }
        );
    }

    /**
     * Show non-blocking toast notification for AJAX cart & UI feedback
     */
    function showWheyToast(message, isError = false) {
        const existing = document.querySelector(".whey-toast");
        if (existing) existing.remove();
        const toast = document.createElement("div");
        toast.className = "whey-toast" + (isError ? " error" : "");
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transition = "opacity 0.25s ease";
            setTimeout(() => toast.remove(), 260);
        }, 2800);
    }

    /**
     * Bind Fly-to-Cart animation + AJAX fetch to any Add-to-Cart form
     */
    function bindAddToCartForm(form) {
        if (!form || form.dataset.gsapBound === "true") return;
        form.dataset.gsapBound = "true";

        form.addEventListener("submit", (e) => {
            if (form.dataset.gsapSubmitting === "true") return;
            e.preventDefault();
            form.dataset.gsapSubmitting = "true";

            const submitBtn = form.querySelector("button[type='submit']");
            const formData = new FormData(form);

            const sendAjax = () => {
                fetch(form.action, {
                    method: "POST",
                    body: formData,
                    headers: { "X-Requested-With": "XMLHttpRequest" }
                })
                    .then((res) => res.json().then((data) => ({ ok: res.ok, data })))
                    .then(({ ok, data }) => {
                        form.dataset.gsapSubmitting = "false";
                        if (ok && data.ok) {
                            if (cartBadge && typeof data.cart_total_items !== "undefined") {
                                cartBadge.textContent = String(data.cart_total_items);
                            }
                            const headerTotal = document.querySelector(".cart-header-total");
                            if (headerTotal && typeof data.cart_total_price !== "undefined") {
                                headerTotal.textContent = `${Number(data.cart_total_price).toLocaleString("vi-VN")}đ`;
                            }
                            bounceCartBadge();
                            showWheyToast(data.message || "Đã thêm vào giỏ hàng!");
                        } else {
                            showWheyToast(data.error || "Không thể thêm sản phẩm vào giỏ.", true);
                        }
                    })
                    .catch(() => {
                        form.dataset.gsapSubmitting = "false";
                        form.submit();
                    });
            };

            if (!submitBtn || !cartBtn) {
                sendAjax();
                return;
            }

            const startRect = submitBtn.getBoundingClientRect();
            const endRect = cartBtn.getBoundingClientRect();

            const orb = document.createElement("div");
            orb.className = "fly-to-cart-orb";
            document.body.appendChild(orb);

            const startX = startRect.left + startRect.width / 2 - 11;
            const startY = startRect.top + startRect.height / 2 - 11;
            const endX = endRect.left + endRect.width / 2 - 11;
            const endY = endRect.top + endRect.height / 2 - 11;

            gsap.set(orb, { x: startX, y: startY, scale: 0.6, autoAlpha: 1 });

            const flyTl = gsap.timeline({
                onComplete: () => {
                    orb.remove();
                    sendAjax();
                }
            });

            flyTl
                .to(
                    submitBtn,
                    {
                        scale: 0.92,
                        duration: 0.1,
                        yoyo: true,
                        repeat: 1,
                        ease: "power2.inOut"
                    },
                    0
                )
                .to(
                    orb,
                    {
                        x: endX,
                        y: endY,
                        scale: 1.2,
                        duration: 0.42,
                        ease: "power3.inOut"
                    },
                    0
                )
                .to(orb, {
                    scale: 0.2,
                    autoAlpha: 0,
                    duration: 0.12
                });
        });
    }

    // Use gsap.matchMedia() for accessibility (prefers-reduced-motion) & responsive control
    const mm = gsap.matchMedia();

    mm.add(
        {
            canAnimate: "(prefers-reduced-motion: no-preference)",
            reduceMotion: "(prefers-reduced-motion: reduce)"
        },
        (context) => {
            const { reduceMotion } = context.conditions;

            if (reduceMotion) {
                gsap.set(".site-header, .fitness-banner, .product-card, .product-detail-container", {
                    autoAlpha: 1,
                    x: 0,
                    y: 0,
                    scale: 1
                });
                gsap.utils.toArray(".nutrition-bar-fill").forEach((bar) => {
                    const targetProgress = parseFloat(bar.dataset.progress || "1");
                    gsap.set(bar, { scaleX: targetProgress });
                });
            } else {
                /* ==================================================================
                   1. Header & Hero Banner Entrance Timeline
                   ================================================================== */
                const introTl = gsap.timeline({
                    defaults: { ease: "power3.out", duration: 0.7 }
                });

                if (document.querySelector(".site-header")) {
                    introTl.from(".site-header", {
                        y: -30,
                        autoAlpha: 0,
                        duration: 0.55,
                        clearProps: "transform,opacity,visibility"
                    });
                }

                const heroItems = gsap.utils.toArray(
                    ".fitness-banner h1, .fitness-banner p, .fitness-banner .banner-tag"
                );
                if (heroItems.length > 0) {
                    introTl.from(
                        heroItems,
                        {
                            y: 35,
                            autoAlpha: 0,
                            stagger: 0.12,
                            ease: "power3.out",
                            clearProps: "transform,opacity,visibility"
                        },
                        "-=0.25"
                    );
                }

                /* ==================================================================
                   2. Product Grid ScrollTrigger.batch()
                   ================================================================== */
                const productCards = gsap.utils.toArray(".product-card");
                if (productCards.length > 0 && typeof ScrollTrigger !== "undefined") {
                    gsap.set(productCards, { y: 50, autoAlpha: 0 });

                    ScrollTrigger.batch(productCards, {
                        interval: 0.1,
                        batchMax: 4,
                        start: "top 90%",
                        onEnter: (batch) => {
                            gsap.to(batch, {
                                y: 0,
                                autoAlpha: 1,
                                duration: 0.65,
                                stagger: 0.1,
                                ease: "power3.out",
                                overwrite: true
                            });
                        },
                        once: true
                    });
                }

                /* ==================================================================
                   3. 3D Card Hover & Micro-interactions (GPU-accelerated transforms)
                   ================================================================== */
                productCards.forEach((card) => {
                    const jarVisual = card.querySelector(
                        ".card-image-box img, .card-image-box .card-image-placeholder"
                    );
                    const buyBtn = card.querySelector(".btn-buy");

                    card.addEventListener("mouseenter", () => {
                        gsap.to(card, {
                            y: -6,
                            duration: 0.3,
                            ease: "power2.out",
                            overwrite: "auto"
                        });

                        if (jarVisual) {
                            gsap.to(jarVisual, {
                                scale: 1.08,
                                y: -6,
                                duration: 0.35,
                                ease: "power2.out",
                                overwrite: "auto"
                            });
                        }

                        if (buyBtn) {
                            buyBtn.classList.add("btn-buy-glow");
                            gsap.to(buyBtn, {
                                scale: 1.06,
                                duration: 0.25,
                                ease: "back.out(1.7)",
                                overwrite: "auto"
                            });
                        }
                    });

                    card.addEventListener("mouseleave", () => {
                        gsap.to(card, {
                            y: 0,
                            duration: 0.3,
                            ease: "power2.out",
                            overwrite: "auto"
                        });

                        if (jarVisual) {
                            gsap.to(jarVisual, {
                                scale: 1,
                                y: 0,
                                duration: 0.35,
                                ease: "power2.out",
                                overwrite: "auto"
                            });
                        }

                        if (buyBtn) {
                            buyBtn.classList.remove("btn-buy-glow");
                            gsap.to(buyBtn, {
                                scale: 1,
                                duration: 0.25,
                                ease: "power2.out",
                                overwrite: "auto"
                            });
                        }
                    });
                });

                /* ==================================================================
                   4. Fly-to-Cart & Cart Badge Elastic Bounce
                   ================================================================== */
                if (cartBtn) {
                    const currentCount = parseInt(cartBtn.dataset.cartCount || "0", 10);
                    const prevCount = parseInt(
                        sessionStorage.getItem("wheystore_cart_prev_count") || "0",
                        10
                    );
                    const justAdded = sessionStorage.getItem("wheystore_cart_just_added") === "1";

                    if (justAdded || currentCount > prevCount) {
                        sessionStorage.removeItem("wheystore_cart_just_added");
                        gsap.delayedCall(0.25, bounceCartBadge);
                    }
                    sessionStorage.setItem("wheystore_cart_prev_count", String(currentCount));
                }

                gsap.utils.toArray(".card-cart-form, .detail-cart-form").forEach(bindAddToCartForm);

                /* ==================================================================
                   5. Product Detail Page: Nutrition Facts Progress Bars & Counters
                   ================================================================== */
                const nutritionPanel = document.getElementById("nutrition-facts");
                if (nutritionPanel && typeof ScrollTrigger !== "undefined") {
                    const bars = gsap.utils.toArray(".nutrition-bar-fill", nutritionPanel);
                    const counters = gsap.utils.toArray(".nutrition-counter", nutritionPanel);

                    gsap.set(bars, { scaleX: 0, transformOrigin: "left center" });

                    const nutritionTl = gsap.timeline({
                        scrollTrigger: {
                            trigger: nutritionPanel,
                            start: "top 85%",
                            toggleActions: "play none none none"
                        }
                    });

                    nutritionTl.to(
                        bars,
                        {
                            scaleX: (i, target) => parseFloat(target.dataset.progress || "0.8"),
                            duration: 1.15,
                            stagger: 0.12,
                            ease: "power3.out"
                        },
                        0
                    );

                    counters.forEach((counterEl, idx) => {
                        const targetVal = parseFloat(counterEl.dataset.target || "0");
                        const decimals = parseInt(counterEl.dataset.decimals || "0", 10);
                        const tracker = { val: 0 };

                        nutritionTl.to(
                            tracker,
                            {
                                val: targetVal,
                                duration: 1.15,
                                ease: "power2.out",
                                onUpdate: () => {
                                    counterEl.textContent = tracker.val.toFixed(decimals);
                                }
                            },
                            idx * 0.12
                        );
                    });
                }
            }

            /* ======================================================================
               6. Fitness Macro Calculator & Supplement Recommender (with GSAP Counter)
               ====================================================================== */
            const analyzeBtn = document.getElementById("btn-analyze-macro");
            const resultsBox = document.getElementById("macro-results-box");
            const catalogScript = document.getElementById("calc-catalog-data");

            if (analyzeBtn && resultsBox && catalogScript) {
                let catalog = [];
                try {
                    catalog = JSON.parse(catalogScript.textContent || "[]");
                } catch (err) {
                    catalog = [];
                }

                analyzeBtn.addEventListener("click", () => {
                    const gender = document.getElementById("calc-gender")?.value || "male";
                    const age = parseFloat(document.getElementById("calc-age")?.value || "23");
                    const height = parseFloat(document.getElementById("calc-height")?.value || "173");
                    const weight = parseFloat(document.getElementById("calc-weight")?.value || "70");
                    const activity = parseFloat(document.getElementById("calc-activity")?.value || "1.55");
                    const goal = document.getElementById("calc-goal")?.value || "lean_bulk";

                    // Mifflin-St Jeor BMR Equation
                    const bmr =
                        gender === "male"
                            ? 10 * weight + 6.25 * height - 5 * age + 5
                            : 10 * weight + 6.25 * height - 5 * age - 161;

                    const tdee = Math.round(bmr * activity);

                    let targetCalories = tdee;
                    let proteinMultiplier = 2.2;
                    let goalLabel = "Tăng cơ nạc (+300 kcal thặng dư sạch)";
                    let scoops = 2;

                    if (goal === "cutting") {
                        targetCalories = Math.max(1200, tdee - 400);
                        proteinMultiplier = 2.4;
                        goalLabel = "Giảm mỡ siết cơ (-400 kcal thâm hụt, giữ cơ tối đa)";
                    } else if (goal === "mass_gain") {
                        targetCalories = tdee + 500;
                        proteinMultiplier = 2.0;
                        goalLabel = "Tăng cân tăng cơ (+500 kcal thặng dư năng lượng)";
                    }

                    const targetProtein = Math.round(weight * proteinMultiplier);
                    scoops = targetProtein >= 165 ? 3 : 2;
                    const wheyGrams = scoops * 25;

                    const goalNoteEl = document.getElementById("res-goal-note");
                    const ratioNoteEl = document.getElementById("res-protein-ratio");
                    const adviceMsgEl = document.getElementById("res-advice-message");
                    const recoContainer = document.getElementById("macro-reco-products");

                    if (goalNoteEl) goalNoteEl.textContent = goalLabel;
                    if (ratioNoteEl) {
                        ratioNoteEl.textContent = `Chuẩn ${proteinMultiplier}g Protein / kg cân nặng (${weight}kg)`;
                    }
                    if (adviceMsgEl) {
                        adviceMsgEl.innerHTML = `🔥 Chỉ cần <strong>${scoops} muỗng mỗi ngày</strong> (cung cấp ngay <strong>${wheyGrams}g Protein</strong> tinh khiết hấp thu nhanh) để đạt mục tiêu <strong>${targetProtein}g Protein/ngày</strong> của bạn!`;
                    }

                    // Select 1-2 best matching products from catalog
                    let recommended = [];
                    if (goal === "cutting") {
                        recommended = catalog.filter(
                            (p) =>
                                p.name.toLowerCase().includes("iso 100") ||
                                p.name.toLowerCase().includes("iso-xp") ||
                                p.name.toLowerCase().includes("hydro whey zero")
                        );
                    } else if (goal === "mass_gain") {
                        recommended = catalog.filter(
                            (p) =>
                                p.name.toLowerCase().includes("muscle mass") ||
                                p.name.toLowerCase().includes("creatine")
                        );
                    } else {
                        recommended = catalog.filter(
                            (p) =>
                                p.name.toLowerCase().includes("rule 1") ||
                                p.name.toLowerCase().includes("c4 original")
                        );
                    }
                    if (recommended.length === 0) {
                        recommended = catalog.slice(0, 2);
                    } else {
                        recommended = recommended.slice(0, 2);
                    }

                    const csrfInput = document.querySelector("input[name='csrfmiddlewaretoken']");
                    const csrfToken = csrfInput ? csrfInput.value : "";

                    if (recoContainer) {
                        recoContainer.innerHTML = recommended
                            .map(
                                (prod) => `
                            <div class="macro-reco-card">
                                <div class="macro-reco-info">
                                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px; flex-wrap:wrap;">
                                        <span class="badge-category" style="position: static; display: inline-block;">${prod.category}</span>
                                        <span class="brand-badge">${prod.brand || "WHEYSTORE"} (${prod.origin || "USA"})</span>
                                        ${prod.discount_percent ? `<span class="badge-discount-red" style="position:static; font-size:0.7rem; padding:2px 7px;">-${prod.discount_percent}%</span>` : ""}
                                    </div>
                                    <h4><a href="${prod.url}">${prod.name}</a></h4>
                                    <div class="macro-reco-meta">
                                        <strong>${prod.protein_per_serving || "25g"} Protein</strong> &bull; <strong>${prod.servings || prod.weight}</strong> &bull; Vị: <strong>${prod.flavor}</strong>
                                    </div>
                                    <div class="macro-reco-price">
                                        ${prod.price_formatted}đ
                                        ${prod.old_price_formatted ? `<del class="old-price-tag" style="margin-left:8px;">${prod.old_price_formatted}đ</del>` : ""}
                                    </div>
                                </div>
                                <form action="${prod.add_cart_url}" method="post" class="card-cart-form">
                                    <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken}">
                                    <input type="hidden" name="quantity" value="1">
                                    <input type="hidden" name="override" value="False">
                                    <button type="submit" class="btn-buy">
                                        <span>&#128722; Thêm vào giỏ ngay</span>
                                    </button>
                                </form>
                            </div>
                        `
                            )
                            .join("") +
                            (recommended.length > 1
                                ? `<div style="margin-top: 10px; text-align: right;">
                                    <button type="button" id="macro-add-all-combo-btn" class="btn-buy">
                                        &#9889; Thêm combo được gợi ý (${recommended.length} món) vào giỏ
                                    </button>
                                   </div>`
                                : "");

                        const addAllBtn = document.getElementById("macro-add-all-combo-btn");
                        if (addAllBtn) {
                            addAllBtn.addEventListener("click", async () => {
                                addAllBtn.disabled = true;
                                for (const prod of recommended) {
                                    const fd = new FormData();
                                    fd.append("csrfmiddlewaretoken", csrfToken);
                                    fd.append("quantity", "1");
                                    fd.append("override", "False");
                                    await fetch(prod.add_cart_url, {
                                        method: "POST",
                                        body: fd,
                                        headers: { "X-Requested-With": "XMLHttpRequest" }
                                    });
                                }
                                showWheyToast(`Đã thêm ${recommended.length} sản phẩm gợi ý vào giỏ!`);
                                window.location.href = "/cart/";
                            });
                        }

                        gsap.utils
                            .toArray(".card-cart-form", recoContainer)
                            .forEach(bindAddToCartForm);
                    }

                    // Show results box & run GSAP Counter + Stagger entrance
                    resultsBox.style.display = "block";

                    const calEl = document.getElementById("res-calories");
                    const proEl = document.getElementById("res-protein");
                    const scoopEl = document.getElementById("res-scoops");

                    const calTracker = { val: 0 };
                    const proTracker = { val: 0 };

                    const calcTl = gsap.timeline({ defaults: { ease: "power3.out" } });
                    calcTl
                        .fromTo(
                            ".macro-metric-card",
                            { y: 24, autoAlpha: 0 },
                            { y: 0, autoAlpha: 1, duration: 0.5, stagger: 0.1 }
                        )
                        .fromTo(
                            ".macro-reco-banner",
                            { y: 20, autoAlpha: 0 },
                            { y: 0, autoAlpha: 1, duration: 0.5 },
                            "-=0.25"
                        )
                        .to(
                            calTracker,
                            {
                                val: targetCalories,
                                duration: 1.1,
                                ease: "power2.out",
                                onUpdate: () => {
                                    if (calEl) calEl.textContent = Math.round(calTracker.val).toLocaleString("vi-VN");
                                }
                            },
                            0
                        )
                        .to(
                            proTracker,
                            {
                                val: targetProtein,
                                duration: 1.1,
                                ease: "power2.out",
                                onUpdate: () => {
                                    if (proEl) proEl.textContent = String(Math.round(proTracker.val));
                                }
                            },
                            0.1
                        );

                    if (scoopEl) scoopEl.textContent = String(scoops);
                });
            }

            /* ======================================================================
               7. Live Search, Price Filter & Sorting with GSAP Flip (60fps)
               ====================================================================== */
            const searchInput = document.getElementById("live-search-input");
            const priceFilter = document.getElementById("live-price-filter");
            const sortSelect = document.getElementById("live-sort-select");
            const productGrid = document.getElementById("product-grid");
            const emptyBox = document.getElementById("live-filter-empty");
            const countLabel = document.getElementById("live-product-count");

            if (productGrid && (searchInput || priceFilter || sortSelect)) {
                const allCards = gsap.utils.toArray(".product-card", productGrid);

                function applyLiveFilterAndSort() {
                    const q = (searchInput?.value || "").trim().toLowerCase();
                    const priceMode = priceFilter?.value || "all";
                    const sortMode = sortSelect?.value || "newest";

                    // Capture layout state before DOM changes with GSAP Flip
                    const flipState =
                        typeof Flip !== "undefined" && !reduceMotion
                            ? Flip.getState(allCards)
                            : null;

                    const matched = [];
                    allCards.forEach((card) => {
                        const name = card.dataset.name || "";
                        const brand = card.dataset.brand || "";
                        const flavor = card.dataset.flavor || "";
                        const price = parseFloat(card.dataset.price || "0");

                        const matchQuery =
                            !q || name.includes(q) || brand.includes(q) || flavor.includes(q);
                        let matchPrice = true;
                        if (priceMode === "under_1m") {
                            matchPrice = price < 1000000;
                        } else if (priceMode === "1m_to_1_8m") {
                            matchPrice = price >= 1000000 && price <= 2000000;
                        } else if (priceMode === "over_1_8m") {
                            matchPrice = price > 2000000;
                        }

                        if (matchQuery && matchPrice) {
                            card.style.display = "flex";
                            matched.push(card);
                        } else {
                            card.style.display = "none";
                        }
                    });

                    // Sort matched cards
                    matched.sort((a, b) => {
                        const priceA = parseFloat(a.dataset.price || "0");
                        const priceB = parseFloat(b.dataset.price || "0");
                        const orderA = parseInt(a.dataset.created || "0", 10);
                        const orderB = parseInt(b.dataset.created || "0", 10);

                        if (sortMode === "price_asc") return priceA - priceB;
                        if (sortMode === "price_desc") return priceB - priceA;
                        return orderA - orderB;
                    });

                    // Re-append sorted cards to grid
                    matched.forEach((card) => productGrid.appendChild(card));

                    if (countLabel) {
                        countLabel.textContent = `${matched.length} sản phẩm có sẵn`;
                    }
                    if (emptyBox) {
                        emptyBox.style.display = matched.length === 0 ? "block" : "none";
                    }

                    // Animate layout transition with GSAP Flip at 60fps
                    if (flipState) {
                        Flip.from(flipState, {
                            duration: 0.45,
                            scale: true,
                            ease: "power3.inOut",
                            stagger: 0.04,
                            onEnter: (elements) =>
                                gsap.fromTo(
                                    elements,
                                    { autoAlpha: 0, scale: 0.88, y: 20 },
                                    { autoAlpha: 1, scale: 1, y: 0, duration: 0.35, ease: "power2.out" }
                                ),
                            onLeave: (elements) =>
                                gsap.to(elements, { autoAlpha: 0, scale: 0.88, duration: 0.25 })
                        });
                    }
                }

                searchInput?.addEventListener("input", applyLiveFilterAndSort);
                priceFilter?.addEventListener("change", applyLiveFilterAndSort);
                sortSelect?.addEventListener("change", applyLiveFilterAndSort);
            }

            // ------------------------------------------------------------
            // 10. MOBILE NAVIGATION DRAWER, SEARCH SUGGEST & STAR PICKER
            // ------------------------------------------------------------
            const mobileToggle = document.getElementById("mobile-menu-toggle");
            const mainNavLinks = document.getElementById("main-nav-links");
            if (mobileToggle && mainNavLinks) {
                mobileToggle.addEventListener("click", () => {
                    const isOpen = mainNavLinks.classList.toggle("open");
                    mobileToggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
                });
            }

            const suggestBox = document.getElementById("search-suggest-box");
            if (searchInput && suggestBox) {
                let suggestTimer = null;
                searchInput.addEventListener("input", () => {
                    clearTimeout(suggestTimer);
                    const q = searchInput.value.trim();
                    if (q.length < 2) {
                        suggestBox.classList.remove("active");
                        suggestBox.innerHTML = "";
                        return;
                    }
                    suggestTimer = setTimeout(() => {
                        fetch(`/api/search-suggest/?q=${encodeURIComponent(q)}`)
                            .then((r) => r.json())
                            .then((data) => {
                                const results = data.results || [];
                                if (results.length === 0) {
                                    suggestBox.classList.remove("active");
                                    suggestBox.innerHTML = "";
                                    return;
                                }
                                suggestBox.innerHTML = results
                                    .map(
                                        (item) =>
                                            `<a href="${item.url}" class="search-suggest-item">
                                                <span>${item.name}${item.brand ? ` (${item.brand})` : ""}</span>
                                                <span class="suggest-price">${Number(item.price).toLocaleString("vi-VN")}đ</span>
                                            </a>`
                                    )
                                    .join("");
                                suggestBox.classList.add("active");
                            })
                            .catch(() => {});
                    }, 220);
                });
                document.addEventListener("click", (evt) => {
                    if (!suggestBox.contains(evt.target) && evt.target !== searchInput) {
                        suggestBox.classList.remove("active");
                    }
                });
            }

            const starPicker = document.querySelector(".star-picker");
            if (starPicker) {
                const targetId = starPicker.dataset.targetSelect;
                const ratingSelect = targetId ? document.getElementById(targetId) : null;
                const starBtns = starPicker.querySelectorAll(".star-btn");
                const updateStars = (val) => {
                    starBtns.forEach((btn) => {
                        const v = parseInt(btn.dataset.value || "0", 10);
                        btn.classList.toggle("active", v <= val);
                    });
                };
                if (ratingSelect) {
                    updateStars(parseInt(ratingSelect.value || "5", 10));
                    starBtns.forEach((btn) => {
                        btn.addEventListener("click", () => {
                            const val = parseInt(btn.dataset.value || "5", 10);
                            ratingSelect.value = String(val);
                            updateStars(val);
                        });
                    });
                }
            }
        }
    );
});

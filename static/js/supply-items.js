(function () {
    const formset = document.querySelector("[data-supply-formset]");
    if (!formset) return;

    const addButton = formset.querySelector("[data-add-supply-item]");
    const emptyForm = formset.querySelector("[data-empty-supply-item]");
    const totalForms = formset.querySelector('input[name$="-TOTAL_FORMS"]');
    const itemList = formset.querySelector(".supply-item-list");

    if (!addButton || !emptyForm || !totalForms || !itemList) return;

    addButton.addEventListener("click", function () {
        const index = Number.parseInt(totalForms.value, 10);
        const html = emptyForm.innerHTML.replace(/__prefix__/g, String(index));
        const template = document.createElement("template");
        template.innerHTML = html.trim();
        const row = template.content.firstElementChild;
        const removeButton = row.querySelector("[data-remove-supply-item]");

        removeButton.addEventListener("click", function () {
            row.remove();
        });

        itemList.append(row);
        totalForms.value = String(index + 1);
    });
})();

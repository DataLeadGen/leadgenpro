/* --- NAYI FILE: static/js/lead_table.js --- */

document.addEventListener('DOMContentLoaded', () => {

    const toggleBtn = document.getElementById('col-toggle-btn');
    const toggleDropdown = document.getElementById('col-toggle-dropdown');
    const checkboxes = document.querySelectorAll('.col-toggle-dropdown input[type="checkbox"]');
    
    // 1. Dropdown ko dikhana / chupana
    if (toggleBtn) {
        toggleBtn.addEventListener('click', (e) => {
            e.stopPropagation(); // Page par click hone se roke
            const isHidden = toggleDropdown.style.display === 'none' || toggleDropdown.style.display === '';
            toggleDropdown.style.display = isHidden ? 'block' : 'none';
        });
    }

    // 2. Bahar click karne par dropdown band karein
    document.addEventListener('click', (e) => {
        if (toggleDropdown && toggleDropdown.style.display === 'block' && !toggleDropdown.contains(e.target)) {
            toggleDropdown.style.display = 'none';
        }
    });

    // 3. User ki saved preferences ko load karna
    // 'columnPrefs' naam se localStorage mein save karenge
    let columnPrefs = JSON.parse(localStorage.getItem('columnPrefs')) || {};

    function toggleColumn(columnName, isVisible) {
        const cells = document.querySelectorAll(`.col-${columnName}`);
        cells.forEach(cell => {
            cell.style.display = isVisible ? '' : 'none';
        });
    }

    // 4. Checkbox change hone par column toggle karein aur save karein
    checkboxes.forEach(checkbox => {
        const colName = checkbox.dataset.col;

        // Page load par, saved preference check karein
        let isVisible;
        if (columnPrefs[colName] !== undefined) {
            // Agar preference saved hai, toh woh use karein
            isVisible = columnPrefs[colName];
        } else {
            // Agar saved nahi hai, toh default CSS (checkbox checked hai ya nahi) use karein
            isVisible = checkbox.checked;
            columnPrefs[colName] = isVisible;
        }

        // Checkbox ko update karein aur column ko toggle karein
        checkbox.checked = isVisible;
        toggleColumn(colName, isVisible);

        // Event listener add karein
        checkbox.addEventListener('change', (e) => {
            const isChecked = e.target.checked;
            const colName = e.target.dataset.col;
            
            // Column ko show/hide karein
            toggleColumn(colName, isChecked);
            
            // Preference ko save karein
            columnPrefs[colName] = isChecked;
            localStorage.setItem('columnPrefs', JSON.stringify(columnPrefs));
        });
    });
    
    // Pehli baar save karein (agar koi preference nahi thi toh)
    localStorage.setItem('columnPrefs', JSON.stringify(columnPrefs));
});
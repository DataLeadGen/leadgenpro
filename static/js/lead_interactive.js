document.addEventListener('DOMContentLoaded', function() {
    
    // --- 1. BULK SELECTION LOGIC ---
    const selectAllCheckbox = document.getElementById('select-all-leads');
    const leadCheckboxes = document.querySelectorAll('.lead-checkbox');
    const bulkActionBar = document.getElementById('bulk-action-bar');
    const selectedCountSpan = document.getElementById('selected-count');

    function updateBulkActionBar() {
        const selectedLeads = document.querySelectorAll('.lead-checkbox:checked');
        const count = selectedLeads.length;

        if (count > 0) {
            selectedCountSpan.textContent = count;
            bulkActionBar.style.display = 'flex';
        } else {
            bulkActionBar.style.display = 'none';
        }

        // 'Select All' ko update karein
        if (selectAllCheckbox) {
            selectAllCheckbox.checked = (count === leadCheckboxes.length) && (count > 0);
        }
    }

    // "Select All" click karne par
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function() {
            leadCheckboxes.forEach(checkbox => {
                checkbox.checked = this.checked;
            });
            updateBulkActionBar();
        });
    }

    // Koi ek row click karne par
    leadCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', updateBulkActionBar);
    });

    // Initial check (agar page refresh hua hai)
    updateBulkActionBar();


    // --- 2. QUICK VIEW DRAWER LOGIC ---
    const drawer = document.getElementById('lead-drawer');
    const overlay = document.getElementById('drawer-overlay');
    const closeBtn = document.getElementById('close-drawer-btn');
    const quickViewButtons = document.querySelectorAll('.quick-view-btn');
    const drawerBody = document.getElementById('drawer-content-body');
    const drawerName = document.getElementById('drawer-full-name');

    function openDrawer() {
        if (drawer && overlay) {
            drawer.classList.add('is-open');
            overlay.classList.add('is-open');
        }
    }

    function closeDrawer() {
        if (drawer && overlay) {
            drawer.classList.remove('is-open');
            overlay.classList.remove('is-open');
        }
    }

    function formatDrawerContent(lead) {
        // Helper function: agar data hai toh dikhao, varna '-'
        const val = (data) => data || '-';
        
        // Helper function: Link banao agar URL hai
        const link = (url, text) => {
            if (!url) return '-';
            // URL ko 'http' se shuru karein agar nahi hai toh
            let cleanUrl = url.startsWith('http') ? url : `https://${url}`;
            return `<a href="${cleanUrl}" target="_blank">${text}</a>`;
        };

        // Drawer ka naya HTML
        return `
            <div class="detail-group">
                <h4>Contact Details</h4>
                <div class="detail-item">
                    <strong>Job Title:</strong>
                    <span>${val(lead.job_title)}</span>
                </div>
                <div class="detail-item">
                    <strong>Prof. Email:</strong>
                    <span>${val(lead.professional_email)}</span>
                </div>
                <div class="detail-item">
                    <strong>Personal Email:</strong>
                    <span>${val(lead.personal_email)}</span>
                </div>
                <div class="detail-item">
                    <strong>Direct Phone:</strong>
                    <span>${val(lead.person_direct_phone)}</span>
                </div>
                <div class="detail-item">
                    <strong>LinkedIn:</strong>
                    <span>${link(lead.person_linkedin_url, 'View Profile')}</span>
                </div>
                <div class="detail-item">
                    <strong>Location:</strong>
                    <span>${val(lead.person_city)}, ${val(lead.person_state)}, ${val(lead.person_country)}</span>
                </div>
            </div>

            <div class="detail-group">
                <h4>Company Details</h4>
                <div class="detail-item">
                    <strong>Company:</strong>
                    <span>${val(lead.company_name)}</span>
                </div>
                <div class="detail-item">
                    <strong>Website:</strong>
                    <span>${link(lead.company_website, val(lead.company_website))}</span>
                </div>
                <div class="detail-item">
                    <strong>Industry:</strong>
                    <span>${val(lead.industry)}</span>
                </div>
                <div class="detail-item">
                    <strong>Employees:</strong>
                    <span>${val(lead.employees)}</span>
                </div>
                 <div class="detail-item">
                    <strong>Revenue:</strong>
                    <span>${val(lead.revenue)}</span>
                </div>
                <div class="detail-item">
                    <strong>Company LinkedIn:</strong>
                    <span>${link(lead.company_linkedin_url, 'View Company Page')}</span>
                </div>
            </div>

            <div class="detail-group">
                <h4>Lead Info</h4>
                <div class="detail-item">
                    <strong>Source:</strong>
                    <span>${val(lead.source)}</span>
                </div>
                 <div class="detail-item">
                    <strong>Comments:</strong>
                    <span>${val(lead.comments)}</span>
                </div>
                 <div class="detail-item">
                    <strong>Added By:</strong>
                    <span>${val(lead.created_by)}</span>
                </div>
                <div class="detail-item">
                    <strong>Added On:</strong>
                    <span>${val(lead.created_at)}</span>
                </div>
                <div class="detail-item">
                    <strong>Last Updated:</strong>
                    <span>${val(lead.updated_at)}</span>
                </div>
            </div>
        `;
    }

    // Har "Quick View" button par click listener lagao
    quickViewButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault(); // Page ko reload hone se roko
            const url = this.dataset.url; // URL ko data attribute se lo

            // Drawer ko "Loading" state mein set karo
            drawerName.textContent = 'Loading...';
            drawerBody.innerHTML = '<p>Loading details...</p>';
            openDrawer();

            // AJAX request se data fetch karo
            fetch(url)
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Network response was not ok');
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.status === 'success') {
                        // Data milne par drawer ko populate karo
                        drawerName.textContent = data.lead.full_name || `${data.lead.first_name} ${data.lead.last_name}`;
                        drawerBody.innerHTML = formatDrawerContent(data.lead);
                    } else {
                        throw new Error(data.message || 'Error fetching lead data');
                    }
                })
                .catch(error => {
                    console.error('Fetch error:', error);
                    drawerBody.innerHTML = `<p style="color: red;">Error: Could not load lead details. ${error.message}</p>`;
                });
        });
    });

    // Drawer ko band karne ke buttons
    if (closeBtn) {
        closeBtn.addEventListener('click', closeDrawer);
    }
    if (overlay) {
        overlay.addEventListener('click', closeDrawer);
    }
    
    
    // --- 3. BULK EXPORT LOGIC (YEH NAYA ADD HUA HAI) ---
    const exportBtn = document.getElementById('bulk-export-btn');

    if (exportBtn) {
        exportBtn.addEventListener('click', function() {
            // 1. Sabhi checked checkboxes ko dhoondein
            const selectedCheckboxes = document.querySelectorAll('.lead-checkbox:checked');
            
            // 2. Unki 'data-lead-id' se ek array banayein
            const leadIds = Array.from(selectedCheckboxes).map(cb => cb.dataset.leadId);

            if (leadIds.length === 0) {
                alert('Please select at least one lead to export.');
                return;
            }

            // 3. IDs ko comma-separated string mein badlein (jaise: "5,12,23")
            const idString = leadIds.join(',');

            // 4. User ko naye URL par bhej dein, jisse download trigger hoga
            window.location.href = `/leads/export-selected/?ids=${idString}`;
        });
    }

});
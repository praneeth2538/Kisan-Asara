let locationLookupSequence = 0;

function fetchLocationDetails() {
    const pincodeField = document.getElementById('pincode');
    const pincodeInput = (pincodeField?.value || '').trim();
    if (pincodeField && pincodeField.value !== pincodeInput) {
        pincodeField.value = pincodeInput;
    }

    const districtInput = document.getElementById('district');
    const mandalInput = document.getElementById('mandal');
    const stateInput = document.getElementById('state');
    const villageSelect = document.getElementById('village');
    const requestSequence = ++locationLookupSequence;

    if (!districtInput || !mandalInput || !villageSelect) {
        return;
    }

    villageSelect.onchange = () => {
        const selectedVillage = villageSelect.selectedOptions[0];
        if (selectedVillage?.dataset.district) {
            districtInput.value = selectedVillage.dataset.district;
        }
        if (selectedVillage?.dataset.mandal) {
            mandalInput.value = selectedVillage.dataset.mandal;
        }
    };

    districtInput.value = '';
    mandalInput.value = '';
    villageSelect.innerHTML = '<option value="" disabled selected>-- Enter Pincode First --</option>';

    if (!/^[1-9][0-9]{5}$/.test(pincodeInput)) {
        if (pincodeInput.length === 6) {
            villageSelect.innerHTML = '<option value="" disabled selected>Enter a valid 6-digit pincode</option>';
        }
        return;
    }

    villageSelect.innerHTML = '<option value="" disabled selected>Loading data...</option>';

    fetch(`/get-location/?pincode=${encodeURIComponent(pincodeInput)}`, {
        method: 'GET',
        headers: { 'Accept': 'application/json' },
    })
        .then(async response => ({ response, data: await response.json() }))
        .then(({ response, data }) => {
            if (
                requestSequence !== locationLookupSequence
                || pincodeField.value.trim() !== pincodeInput
            ) {
                return;
            }

            if (data.success) {
                if (stateInput && data.state) {
                    stateInput.value = data.state;
                }
                districtInput.value = data.district || '';
                mandalInput.value = data.mandal || '';

                villageSelect.innerHTML = '<option value="" disabled selected>-- Select Village --</option>';
                (data.villages || []).forEach(village => {
                    const option = document.createElement('option');
                    option.value = village;
                    option.text = village;
                    const villageLocation = data.village_locations?.[village];
                    if (villageLocation) {
                        option.dataset.district = villageLocation.district || '';
                        option.dataset.mandal = villageLocation.mandal || '';
                    }
                    villageSelect.appendChild(option);
                });
                if ((data.villages || []).length === 0) {
                    villageSelect.innerHTML = '<option value="" disabled selected>No villages found</option>';
                }
            } else {
                const message = response.status === 404
                    ? 'Pincode not found. Check and try again.'
                    : response.status === 400
                        ? 'Enter a valid 6-digit pincode.'
                        : 'This pincode is unavailable.';
                villageSelect.innerHTML = `<option value="" disabled selected>${message}</option>`;
            }
        })
        .catch(error => {
            if (requestSequence !== locationLookupSequence) {
                return;
            }
            console.error('Error fetching location:', error);
            villageSelect.innerHTML = '<option value="" disabled selected>Location unavailable. Try again.</option>';
        });
}

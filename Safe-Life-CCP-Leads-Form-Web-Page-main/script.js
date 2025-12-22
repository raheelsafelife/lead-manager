let currentStep = 0;
const steps = document.querySelectorAll('.step');
const totalSteps = steps.length - 1; // Thank-you step excluded

// Initialize progress bar on page load
document.addEventListener('DOMContentLoaded', () => {
  updateProgressBar();

  // Re-attach conditional field logic on load
  document.getElementById('know_birthdate').addEventListener('change', toggleBirthOrAgeField);
  document.getElementById('provide_address').addEventListener('change', toggleAddressOrCounty);
  document.getElementById('source').addEventListener('change', () => {
    toggleOtherSourceField();
    toggleSocDateField();
  });
  toggleAddressOrCounty();
  toggleOtherSourceField();
  toggleSocDateField();
});

function validateStep(stepIndex) {
  // Step 0: Staff Identification
  if (stepIndex === 0) {
    const staffNameField = document.getElementById('staff_name');
    const staffNameError = document.getElementById('staffNameError');
    const userIdField = document.getElementById('user_id');
    const userIdError = document.getElementById('userIdError');
    const sourceField = document.getElementById('source');
    const sourceError = document.getElementById('sourceError');

    const staffNameValue = staffNameField.value.trim();
    const userIdValue = userIdField.value.trim();
    const sourceValue = sourceField.value;

    // Reset errors
    staffNameError.style.display = "none";
    userIdError.style.display = "none";
    sourceError.style.display = "none";

    if (!staffNameValue) {
      staffNameError.textContent = "Please enter your staff name.";
      staffNameError.style.display = "block";
      return;
    }

    if (!userIdValue) {
      userIdError.textContent = "Please enter your staff ID.";
      userIdError.style.display = "block";
      return;
    }

    if (!sourceValue) {
      sourceError.textContent = "Please select a lead source.";
      sourceError.style.display = "block";
      return;
    }

    if (sourceValue === 'Other') {
      const otherSourceField = document.getElementById('other_source');
      const otherSourceError = document.getElementById('otherSourceError');
      const otherSourceValue = otherSourceField.value.trim();

      if (!otherSourceValue) {
        otherSourceError.textContent = "Please specify the other source.";
        otherSourceError.style.display = "block";
        return;
      }
      otherSourceError.style.display = "none";
    }

    if (sourceValue === 'Transfer') {
      const socDateField = document.getElementById('soc_date');
      const socDateError = document.getElementById('socDateError');
      const socDateValue = socDateField.value;

      if (!socDateValue) {
        socDateError.textContent = "Please enter the SOC Date for transfer.";
        socDateError.style.display = "block";
        return;
      }
      socDateError.style.display = "none";
    }

    nextStep();
    return;
  }

  // Step 1: Client Info (Name, Relation, Priority)
  if (stepIndex === 1) {
    const nameField = document.getElementById('name');
    const nameError = document.getElementById('nameError');
    const relationField = document.getElementById('relation');
    const relationError = document.getElementById('relationError');

    const nameValue = nameField.value.trim();
    const relationValue = relationField.value.trim();

    let isValid = true;

    if (!nameValue) {
      nameError.textContent = "Please enter the client's name.";
      nameError.style.display = "block";
      isValid = false;
    } else {
      nameError.style.display = "none";
    }

    if (!relationValue) {
      relationError.textContent = "Please enter your relation with the client.";
      relationError.style.display = "block";
      isValid = false;
    } else {
      relationError.style.display = "none";
    }

    if (isValid) nextStep();
    return;
  }

  // Step 2: Client Details (Birthdate, Medicaid, Phone/Email)
  if (stepIndex === 2) {
    const knowBirthdate = document.getElementById('know_birthdate').value;
    const knowBirthdateError = document.getElementById('knowBirthdateError');
    const medicaidDropdown = document.getElementById('medicaid');
    const medicaidError = document.getElementById('medicaidError');
    const phoneField = document.getElementById('phone');
    const emailField = document.getElementById('email');
    const phoneError = document.getElementById('phoneError');
    const emailError = document.getElementById('emailError');

    let isValid = true;

    // Birthdate validation
    knowBirthdateError.style.display = "none";
    if (!knowBirthdate) {
      knowBirthdateError.textContent = "Please select Yes or No.";
      knowBirthdateError.style.display = "block";
      isValid = false;
    } else if (knowBirthdate === 'yes') {
      const birthdateField = document.getElementById('birthdate');
      const birthdateError = document.getElementById('birthdateError');
      const birthdateValue = birthdateField.value.trim();
      const birthdatePattern = /^(0[1-9]|1[0-2])\/(0[1-9]|[12][0-9]|3[01])\/(19|20)\d{2}$/;

      if (!birthdateValue) {
        birthdateError.textContent = "Please enter the birthdate.";
        birthdateError.style.display = "block";
        isValid = false;
      } else if (!birthdatePattern.test(birthdateValue)) {
        birthdateError.textContent = "Enter a valid date in mm/dd/yyyy format.";
        birthdateError.style.display = "block";
        isValid = false;
      } else {
        birthdateError.style.display = "none";
      }
    } else if (knowBirthdate === 'no') {
      const ageField = document.getElementById('age');
      const ageError = document.getElementById('ageError');
      const ageValue = ageField.value.trim();
      if (!ageValue) {
        ageError.textContent = "Please enter the client's age.";
        ageError.style.display = "block";
        isValid = false;
      } else if (isNaN(ageValue) || ageValue <= 0 || ageValue > 120) {
        ageError.textContent = "Enter a valid age (1–120).";
        ageError.style.display = "block";
        isValid = false;
      } else {
        ageError.style.display = "none";
      }
    }

    // Medicaid validation
    medicaidError.style.display = "none";
    if (!medicaidDropdown.value) {
      medicaidError.textContent = "Please select Yes or No.";
      medicaidError.style.display = "block";
      isValid = false;
    }

    // Contact validation
    phoneError.style.display = "none";
    emailError.style.display = "none";
    if (!phoneField.value.trim() && !emailField.value.trim()) {
      phoneError.textContent = "Provide at least Phone or Email.";
      phoneError.style.display = "block";
      isValid = false;
    } else {
      if (phoneField.value.trim()) {
        const phoneValue = phoneField.value.trim();
        const phoneRegex = /^(\d{10}|\d{3}-\d{3}-\d{4})$/;
        if (!phoneRegex.test(phoneValue)) {
          phoneError.textContent = "Invalid format (1234567890 or 123-456-7890).";
          phoneError.style.display = "block";
          isValid = false;
        }
      }
      if (emailField.value.trim() && !/^[\w-.]+@([\w-]+\.)+[\w-]{2,4}$/.test(emailField.value.trim())) {
        emailError.textContent = "Invalid email address.";
        emailError.style.display = "block";
        isValid = false;
      }
    }

    if (isValid) nextStep();
    return;
  }

  // Step 3: Address Question + Fields
  if (stepIndex === 3) {
    const provide = document.getElementById('provide_address').value;
    const provideError = document.getElementById('provideAddressError');
    provideError.style.display = 'none';

    if (!provide) {
      provideError.textContent = "Please select Yes or No.";
      provideError.style.display = 'block';
      return;
    }

    let valid = true;

    if (provide === 'yes') {
      const line1 = document.getElementById('address_line1');
      const line1Err = document.getElementById('addressLine1Error');
      const cityYes = document.getElementById('city_yes');
      const cityYesErr = document.getElementById('cityYesError');
      const stateField = document.getElementById('state');
      const stateErr = document.getElementById('stateError');
      const zipYes = document.getElementById('zip_yes');
      const zipYesErr = document.getElementById('zipYesError');

      [line1Err, cityYesErr, stateErr, zipYesErr].forEach(e => e.style.display = 'none');

      if (!line1.value.trim()) {
        line1Err.textContent = "Address Line 1 is required.";
        line1Err.style.display = 'block';
        valid = false;
      }

      if (!/^[A-Za-z ]+$/.test(cityYes.value.trim())) {
        cityYesErr.textContent = "City can only contain letters and spaces.";
        cityYesErr.style.display = 'block';
        valid = false;
      }

      const st = stateField.value.trim().toUpperCase();
      stateField.value = st;
      if (!/^[A-Z]{2}$/.test(st)) {
        stateErr.textContent = "State must be exactly 2 letters.";
        stateErr.style.display = 'block';
        valid = false;
      }

      if (!/^\d{5}$/.test(zipYes.value.trim())) {
        zipYesErr.textContent = "Enter a valid 5-digit Zip Code.";
        zipYesErr.style.display = 'block';
        valid = false;
      }
    } else if (provide === 'no') {
      const cityNo = document.getElementById('city_no');
      const cityNoErr = document.getElementById('cityNoError');
      const zipNo = document.getElementById('zip_no');
      const zipNoErr = document.getElementById('zipNoError');

      [cityNoErr, zipNoErr].forEach(e => e.style.display = 'none');

      if (!/^[A-Za-z ]+$/.test(cityNo.value.trim())) {
        cityNoErr.textContent = "City can only contain letters and spaces.";
        cityNoErr.style.display = 'block';
        valid = false;
      }
      if (!/^\d{5}$/.test(zipNo.value.trim())) {
        zipNoErr.textContent = "Enter a valid 5-digit Zip Code.";
        zipNoErr.style.display = 'block';
        valid = false;
      }
    }

    if (valid) nextStep();
    return;
  }

  // Step 4: Additional Info
  if (stepIndex === 4) {
    nextStep();
    return;
  }
}

// Move to the next step
function nextStep() {
  if (currentStep < totalSteps) {
    steps[currentStep].classList.remove('active');
    currentStep++;
    steps[currentStep].classList.add('active');
    updateProgressBar();
  }
}

// Move to the previous step
function prevStep() {
  if (currentStep > 0) {
    steps[currentStep].classList.remove('active');
    currentStep--;
    steps[currentStep].classList.add('active');
    updateProgressBar();
  }
}

// Update the progress bar and step indicator
function updateProgressBar() {
  const progressBar = document.getElementById('progressBar');
  const stepIndicator = document.getElementById('stepIndicator');

  if (currentStep >= totalSteps) {
    progressBar.style.width = `100%`;
    stepIndicator.textContent = `Step ${totalSteps} of ${totalSteps}`;
  } else {
    const progress = (currentStep / totalSteps) * 100;
    progressBar.style.width = `${progress}%`;
    stepIndicator.textContent = `Step ${currentStep + 1} of ${totalSteps}`;
  }
}

function toggleBirthOrAgeField() {
  const know = document.getElementById('know_birthdate').value;
  document.getElementById('birthdateContainer').style.display = (know === 'yes') ? 'block' : 'none';
  document.getElementById('ageContainer').style.display = (know === 'no') ? 'block' : 'none';
}

function toggleMedicaidField() {
  const medicaid = document.getElementById('medicaid').value;
  const medicaidContainer = document.getElementById('medicaidNumberContainer');
  medicaidContainer.style.display = (medicaid === 'yes') ? 'block' : 'none';
}

function toggleOtherSourceField() {
  const source = document.getElementById('source').value;
  const container = document.getElementById('otherSourceContainer');
  container.style.display = (source === 'Other') ? 'block' : 'none';
}

function toggleSocDateField() {
  const source = document.getElementById('source').value;
  const container = document.getElementById('socDateContainer');
  container.style.display = (source === 'Transfer') ? 'block' : 'none';
}

function toggleAddressOrCounty() {
  const provide = document.getElementById('provide_address').value;

  const yesGroup = document.querySelectorAll('#addressFields input');
  const noGroup = document.querySelectorAll('#countyCityZipContainer input');

  if (provide === 'yes') {
    document.getElementById('addressFields').style.display = 'block';
    document.getElementById('countyCityZipContainer').style.display = 'none';
    yesGroup.forEach(i => i.disabled = false);
    noGroup.forEach(i => i.disabled = true);
  } else if (provide === 'no') {
    document.getElementById('addressFields').style.display = 'none';
    document.getElementById('countyCityZipContainer').style.display = 'block';
    yesGroup.forEach(i => i.disabled = true);
    noGroup.forEach(i => i.disabled = false);
  } else {
    document.getElementById('addressFields').style.display = 'none';
    document.getElementById('countyCityZipContainer').style.display = 'none';
    yesGroup.forEach(i => i.disabled = true);
    noGroup.forEach(i => i.disabled = true);
  }
}

function restartForm() {
  const form = document.getElementById('leadForm');
  form.reset();
  document.getElementById('birthdateContainer').style.display = 'none';
  document.getElementById('ageContainer').style.display = 'none';
  document.getElementById('medicaidNumberContainer').style.display = 'none';
  document.getElementById('addressFields').style.display = 'none';
  document.getElementById('countyCityZipContainer').style.display = 'none';
  document.getElementById('otherSourceContainer').style.display = 'none';
  document.getElementById('socDateContainer').style.display = 'none';

  document.querySelectorAll('.error-message, .error').forEach(el => {
    el.textContent = '';
    el.style.display = 'none';
  });

  const submitButton = form.querySelector('button[type="submit"]');
  if (submitButton) {
    submitButton.disabled = false;
    submitButton.textContent = 'Submit';
  }

  steps.forEach(s => s.classList.remove('active'));
  currentStep = 0;
  steps[0].classList.add('active');
  updateProgressBar();
}

document.getElementById('leadForm').addEventListener('submit', async function (e) {
  e.preventDefault();
  const submitButton = this.querySelector('button[type="submit"]');
  if (submitButton.disabled) return;

  submitButton.disabled = true;
  submitButton.textContent = "Submitting...";

  const formData = new FormData(this);
  const data = Object.fromEntries(formData);

  if (data.source === 'Other' && data.other_source) {
    data.source = data.other_source;
  }

  try {
    const response = await fetch('http://localhost:8000/api/external-lead', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });

    if (!response.ok) {
      console.error('Server error:', response.statusText);
      submitButton.disabled = false;
      submitButton.textContent = "Submit";
      return;
    }

    steps[currentStep].classList.remove('active');
    currentStep = totalSteps;
    steps[currentStep].classList.add('active');
    updateProgressBar();
  } catch (err) {
    console.error('Error submitting form:', err);
    submitButton.disabled = false;
    submitButton.textContent = "Submit";
  }
});

if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/service-worker.js')
    .then(() => console.log('Service Worker Registered'))
    .catch(err => console.error('Service Worker Failed:', err));
}

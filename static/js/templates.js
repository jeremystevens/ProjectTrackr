// JavaScript for template loading
document.addEventListener("DOMContentLoaded", function() {
  console.log("Template.js loaded");
  const templateSelector = document.getElementById("template-selector");
  if (templateSelector) {
    templateSelector.addEventListener("change", function() {
      const templateId = parseInt(this.value);
      console.log("Template selected:", templateId);
      if (templateId <= 0) return;
      const contentArea = document.getElementById("content-area") || document.getElementById("content");
      const syntaxSelector = document.getElementById("syntax");
      if (!contentArea || !syntaxSelector) return;
      if (contentArea.value && !confirm("Replace content with template?")) return;
      const xhr = new XMLHttpRequest();
      xhr.open("GET", "/template/" + templateId, true);
      xhr.onreadystatechange = function() {
        if (xhr.readyState === 4) {
          console.log("Response status:", xhr.status);
          if (xhr.status === 200) {
            const data = JSON.parse(xhr.responseText);
            console.log("Template data:", data);
            contentArea.value = data.content;
            syntaxSelector.value = data.syntax;
            console.log("Applied template:", data.name);
          }
        }
      };
      xhr.send();
    });
  }
});

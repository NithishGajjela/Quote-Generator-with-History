const quoteText = document.querySelector("#quote-text");
const quoteAuthor = document.querySelector("#quote-author span");
const newQuoteButton = document.querySelector("#new-quote-button");
const buttonLabel = document.querySelector(".button-label");
const quoteError = document.querySelector("#quote-error");
const historyError = document.querySelector("#history-error");
const historyList = document.querySelector("#history-list");
const historyEmpty = document.querySelector("#history-empty");
const historyCount = document.querySelector("#history-count");

function showMessage(element, message) {
  element.textContent = message;
  element.hidden = !message;
}

function formatDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Saved date unavailable";
  }
  return date.toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function makeHistoryItem(quote) {
  const item = document.createElement("li");
  item.className = "history-item";

  const content = document.createElement("div");
  const text = document.createElement("p");
  text.className = "history-quote";
  text.textContent = `“${quote.text}”`;

  const author = document.createElement("p");
  author.className = "history-author";
  author.textContent = `— ${quote.author}`;
  content.append(text, author);

  const savedAt = document.createElement("time");
  savedAt.className = "history-date";
  savedAt.dateTime = quote.created_at;
  savedAt.textContent = formatDate(quote.created_at);

  item.append(content, savedAt);
  return item;
}

async function loadHistory() {
  try {
    const response = await fetch("/api/quotes/history");
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "We couldn't load your saved quotes.");
    }

    historyList.replaceChildren(...data.map(makeHistoryItem));
    historyCount.textContent = `${data.length} saved`;
    historyEmpty.hidden = data.length > 0;
    showMessage(historyError, "");
  } catch (error) {
    showMessage(historyError, error.message || "We couldn't load your saved quotes.");
  }
}

async function requestNewQuote() {
  newQuoteButton.disabled = true;
  buttonLabel.textContent = "Finding a quote…";
  showMessage(quoteError, "");

  try {
    const response = await fetch("/api/quotes/random", { method: "POST" });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "We couldn't find a quote. Please try again.");
    }

    quoteText.textContent = `“${data.text}”`;
    quoteAuthor.textContent = data.author;
    await loadHistory();
  } catch (error) {
    showMessage(quoteError, error.message || "We couldn't find a quote. Please try again.");
  } finally {
    newQuoteButton.disabled = false;
    buttonLabel.textContent = "New Quote";
  }
}

newQuoteButton.addEventListener("click", requestNewQuote);
loadHistory();

export const PIPELINE_STEPS = {
  rewrite: [
    { label: "Reading input" },
    { label: "Fetching author style" },
    { label: "Generating candidates" },
    { label: "Ranking best version" },
    { label: "Finalizing output" },
  ],
  continue: [
    { label: "Analyzing your text" },
    { label: "Loading author voice" },
    { label: "Building continuation" },
    { label: "Refining flow" },
    { label: "Polishing result" },
  ],
  analyze: [
    { label: "Tokenizing input" },
    { label: "Computing embeddings" },
    { label: "Detecting style signals" },
    { label: "Matching author profiles" },
    { label: "Building report" },
  ],
};

export const MICROCOPY = {
  rewrite: [
    "Matching author voice...",
    "Preserving your meaning...",
    "Avoiding repetition...",
    "Polishing final wording...",
    "Comparing candidate versions...",
    "Selecting the best rewrite...",
  ],
  continue: [
    "Extending the narrative...",
    "Maintaining story flow...",
    "Channeling the author's rhythm...",
    "Building on your ideas...",
    "Crafting the continuation...",
  ],
  analyze: [
    "Mapping semantic space...",
    "Detecting emotion layers...",
    "Comparing to known authors...",
    "Measuring confidence signals...",
    "Scanning writing patterns...",
  ],
};

export const AUTHOR_TRAITS = {
  "William Shakespeare": [
    '"Brevity is the soul of wit."',
    "Known for: iambic pentameter, rich metaphors",
    "Style: poetic, dramatic, layered meaning",
  ],
  "Jane Austen": [
    '"It is a truth universally acknowledged..."',
    "Known for: irony, social commentary",
    "Style: elegant, witty, observational",
  ],
  "Charles Dickens": [
    '"It was the best of times, it was the worst of times."',
    "Known for: vivid characters, social critique",
    "Style: descriptive, emotional, sweeping",
  ],
  "Mark Twain": [
    '"The secret of getting ahead is getting started."',
    "Known for: colloquial language, humor, satire",
    "Style: conversational, sharp, direct",
  ],
  "Ernest Hemingway": [
    '"Write hard and clear about what hurts."',
    "Known for: iceberg theory, sparse prose",
    "Style: minimalist, direct, understated",
  ],
  "Virginia Woolf": [
    '"You cannot find peace by avoiding life."',
    "Known for: stream of consciousness",
    "Style: lyrical, introspective, flowing",
  ],
};

export const TAB_META = {
  rewrite: {
    label: "Rewrite",
    desc: "Transform text into an author's voice",
    icon: "R",
  },
  continue: {
    label: "Continue",
    desc: "Extend a story in an author's style",
    icon: "C",
  },
  analyze: {
    label: "Analyze",
    desc: "Detect writing patterns and style signals",
    icon: "A",
  },
};

export function getAuthorTrait(authorName) {
  const traits = AUTHOR_TRAITS[authorName];
  if (!traits) return `Working in ${authorName}'s style`;

  const stableIndex = Array.from(authorName).reduce(
    (sum, char) => sum + char.charCodeAt(0),
    0,
  ) % traits.length;

  return traits[stableIndex];
}

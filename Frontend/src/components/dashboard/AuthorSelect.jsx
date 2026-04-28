export default function AuthorSelect({ authors, value, onChange, disabled }) {
  return (
    <select
      className="author-select"
      value={value}
      onChange={(event) => onChange(event.target.value)}
      disabled={disabled}
      aria-label="Choose author style"
    >
      <option value="">Choose author style</option>
      {authors.map((author) => (
        <option key={author} value={author}>
          {author}
        </option>
      ))}
    </select>
  );
}

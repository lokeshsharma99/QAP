// Shared QAP logo for all auth pages — matches src/app/icon.svg
export default function QapLogo({ size = 56 }: { size?: number }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 32 32"
      width={size}
      height={size}
      aria-label="Quality Autopilot"
    >
      <rect width="32" height="32" rx="6" fill="#FF4017" />
      <text
        x="50%"
        y="50%"
        dominantBaseline="central"
        textAnchor="middle"
        fontFamily="Arial, sans-serif"
        fontWeight="bold"
        fontSize="14"
        fill="#ffffff"
      >
        QAP
      </text>
    </svg>
  )
}

import { Toaster as Sonner } from 'sonner'

type ToasterProps = React.ComponentProps<typeof Sonner>

const Toaster = ({ ...props }: ToasterProps) => {
  return (
    <Sonner
      theme="dark"
      className="toaster group"
      toastOptions={{
        classNames: {
          toast:
            'group toast group-[.toaster]:bg-primaryAccent group-[.toaster]:text-primary group-[.toaster]:border-accent group-[.toaster]:shadow-lg',
          description: 'group-[.toast]:text-muted',
          actionButton: 'group-[.toast]:bg-primary group-[.toast]:text-primaryAccent',
          cancelButton: 'group-[.toast]:bg-accent group-[.toast]:text-muted'
        }
      }}
      {...props}
    />
  )
}

export { Toaster }

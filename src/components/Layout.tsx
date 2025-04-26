
import { SidebarProvider, Sidebar, SidebarContent, SidebarGroup, SidebarHeader, SidebarFooter, SidebarMenu, SidebarMenuItem, SidebarMenuButton } from "@/components/ui/sidebar"
import { Button } from "./ui/button"
import { Menu, PanelLeft } from "lucide-react"

const Layout = ({ children }: { children: React.ReactNode }) => {
  return (
    <SidebarProvider>
      <div className="min-h-screen flex w-full">
        <Sidebar>
          <SidebarHeader className="border-b py-4">
            <h2 className="px-4 font-semibold">Content Checker</h2>
          </SidebarHeader>
          <SidebarContent>
            <SidebarGroup>
              <SidebarMenu>
                <SidebarMenuItem>
                  <SidebarMenuButton asChild>
                    <Button variant="ghost" className="w-full justify-start">
                      <PanelLeft className="mr-2" />
                      Check Content
                    </Button>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              </SidebarMenu>
            </SidebarGroup>
          </SidebarContent>
          <SidebarFooter className="border-t p-4">
            <p className="text-sm text-muted-foreground">
              © {new Date().getFullYear()} Content Checker
            </p>
          </SidebarFooter>
        </Sidebar>
        <div className="flex-1">
          <header className="border-b">
            <div className="flex items-center h-14 px-4 lg:px-6">
              <Button variant="ghost" size="icon" className="md:hidden">
                <Menu className="h-6 w-6" />
              </Button>
              <h1 className="text-lg font-semibold">Content Checker</h1>
            </div>
          </header>
          <main className="flex-1">{children}</main>
          <footer className="border-t py-4 px-4 lg:px-6">
            <p className="text-sm text-muted-foreground text-center">
              Powered by AI - Check your content for originality
            </p>
          </footer>
        </div>
      </div>
    </SidebarProvider>
  )
}

export default Layout

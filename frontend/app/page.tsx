import Simulator from "@/components/Simulator";

// The page itself is a Server Component: it just renders the interactive part,
// which runs in the browser and talks to the Python API.
export default function Home() {
  return <Simulator />;
}

import "./App.css"

function UserDetails({ userData }) {
  return (
    <div>
      <p>This is the user dtails component</p>
      <p>Name: {userData.name}</p>
      <p>Email: {userData.email}</p>
    </div>
  )
}


function ProfilePage({ userData }) {
  return (
    <div>
      <p>Profile page starts here, passed onto the userdetails</p>
      <UserDetails userData={userData}></UserDetails>
    </div>
  )
}
function App() {
  const userData = {
    name: "Jane Doe",
    email: "daniel@komolafe.com"
  };
  return (
    <div className="text-body">
      This is the entrypoint
      that is what I'm trying to do
      <ProfilePage userData={userData}></ProfilePage>
      <button className="font-body text-body text-primary-hover">press me</button>

    </div>
  )
}

export default App

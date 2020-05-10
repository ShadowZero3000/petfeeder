Vue.component('healthchecks', {
  data: function () {
    return {
      events: []
    }
  },
  methods: {
    getData() {
      axios
        .get('//'+window.location.host+'/api/event/healthcheck')
        .then(response => {
          me = this
          this.events = response.data
        })
    },
  },
  mounted () {
    this.getData()
  },
  template: `
<template>
  <b-container-fluid>
    <div class="row">
      <div class="col col-sm-10"><h1>Health Check Schedule</h1></div>
    </div>
    <div v-if="events.length > 0">
      <table class="table table-striped">
        <thead>
          <tr>
            <th scope="col">Name</th>
            <th scope="col">Time</th>
            <th scope="col">Check ID</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="event in events">
            <td scope="col">{{ event.details.name }}</td>
            <td scope="col">{{ event.details.time }}</td>
            <td scope="col">{{ event.details.check_id }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </b-container-fluid>
</template>
`
})

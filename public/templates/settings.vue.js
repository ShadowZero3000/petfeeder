Vue.component('settings', {
  data: function () {
    return {
      settings: []
    }
  },
  methods: {
    getData() {
      //TODO
    },
  },
  mounted () {
    this.getData()
  },
  template: `
<template>
  <b-container-fluid>
    <div class="row">
      <div class="col col-sm-10"><h1>Settings</h1></div>
    </div>
    <div v-if="settings.length > 0">
      <table class="table table-striped">
        <thead>
          <tr>
            <th scope="col">Name</th>
            <th scope="col">Time</th>
            <th scope="col">Check ID</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="setting in settings">
            <td scope="col">{{ setting.details.name }}</td>
            <td scope="col">{{ setting.details.time }}</td>
            <td scope="col">{{ setting.details.check_id }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </b-container-fluid>
</template>
`
})

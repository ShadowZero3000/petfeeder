Vue.component('cards', {
  data: function () {
    return {
      events: []
    }
  },
  template: `
<template>
  <b-container>
    <div v-if="events">
      <b-row>
        {{ events}}waitwhat
        <!-- <div v-bind:key="data.index" v-for="data in meals">
          <b-col l="4">
            <b-card
              img-alt="Image"
              img-top
              tag="article"
              style="max-width: 20rem;"
              class="mb-2">
              <b-button href="#" variant="primary">View food</b-button>
            </b-card>
          </b-col> -->
        </div>
      </b-row>
    </div>
    <div v-else>
      <h5>No Events available yet</h5>
    </div>
  </b-container>
</template>
`
})

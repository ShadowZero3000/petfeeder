Vue.component('meals', {
  data: function () {
    return {
      events: [],
      fields: [
        {"label":"Name","key":"details.name"},
        {"label":"Time","key":"details.time"},
        {"label":"Servings","key":"details.servings"},
        {"label":"Notify","key":"notify"},
        {"label":"", "key":"details"}
      ],
      editorMode: null,
      editRow: null,
      mealEditor: {
        "name": "",
        "time": "",
        "servings": "",
        "notify": false
      },
      mealEditorState: {},
      errorString: null
    }
  },
  methods: {
    getData() {
      axios
        .get('//'+window.location.host+'/api/event/meal')
        .then(response => {
          me = this
          this.events = _.sortBy(response.data, ['details.time', 'details.name'])
        })
    },
    feed() {
      axios
        .post('//'+window.location.host+'/api/feed', {"servings":1})
        .then(response => {
          me = this
        })
    },
    remove(row) {
      console.log(row)
      axios
        .delete('//'+window.location.host+'/api/event/'+row.item.id)
        .then(response => {
          me = this
          this.getData()
        })
        .catch(error => {
          console.log("We should handle errors on delete")
        })

    },
    add() {
      axios
        .post('//'+window.location.host+'/api/event/meal', this.mealEditor)
        .then(response => {
          me = this
          this.getData()
          this.$nextTick(() => {
            this.$bvModal.hide('mealEditorModal')
          })
        })
        .catch(error => {
          this.errorString = "Request failed"
          this.errorString = error.response.data.status_details.description
        })
    },
    edit(id) {
      axios
        .put('//'+window.location.host+'/api/event/meal/'+id, this.mealEditor)
        .then(response => {
          me = this
          this.getData()
          this.$nextTick(() => {
            this.$bvModal.hide('mealEditorModal')
          })
        })
        .catch(error => {
          this.errorString = "Request failed"
          this.errorString = error.response.data.status_details.description
        })
    },
    checkFormValidity() {
      const valid = this.$refs.mealEditorForm.checkValidity()
      this.mealEditorState = valid
      return valid
    },
    am_pm_to_hours(time) {
        console.log(time);
        var hours = Number(time.match(/^(\d+)/)[1]);
        var minutes = Number(time.match(/:(\d+)/)[1]);
        var AMPM = time.match(/\s(.*)$/)[1];
        if (AMPM == "pm" && hours < 12) hours = hours + 12;
        if (AMPM == "am" && hours == 12) hours = hours - 12;
        var sHours = hours.toString();
        var sMinutes = minutes.toString();
        if (hours < 10) sHours = "0" + sHours;
        if (minutes < 10) sMinutes = "0" + sMinutes;
        return (sHours +':'+sMinutes);
    },
    loadModal() {
      this.resetModal()
      if(this.editorMode == "Edit") {
        this.mealEditor = _.clone(this.editRow.item.details)
        this.mealEditor.time = this.am_pm_to_hours(this.mealEditor.time.toLowerCase())
      }
    },
    resetModal() {
      console.debug
      this.mealEditor.name = ""
      this.mealEditor.time = "7:00:00"
      this.mealEditor.servings = ""
      this.errorString = null
      this.mealEditorState = {}
    },
    handleOk(bvModalEvt) {
      // Prevent modal from closing
      bvModalEvt.preventDefault()
      // Trigger submit handler
      this.handleSubmit()
    },
    handleSubmit() {
      // Exit when the form isn't valid
      if (!this.checkFormValidity()) {
        return
      }
      if(this.editorMode == "Add") {
        this.add()
      } else {
        this.edit(this.editRow.item.id)
      }
    }
  },
  mounted () {
    this.getData()
  },
  template: `
<template>
  <b-container-fluid>
    <div class="row">
      <div class="col-md-6 mr-auto"><h1>Meal Schedule</h1></div>
      <div class="clearfix visible-xs-block"></div>
      <div class="col-md-3">
        <button class="btn btn-success btn-lg btn-block" role="button" @click="editorMode='Add'" v-b-modal.mealEditorModal>Add New</button>
      </div>
      <div class="col-md-3">
        <button class="btn btn-primary btn-lg btn-block" role="button" v-on:click="feed">Feed now</button>
      </div>
    </div>
    <div v-if="events.length > 0">
      <b-table striped :items="events" :fields="fields" >
        <template v-slot:cell(notify)="row">
          <div v-if="row.item.details.notify" class="far fa-comment" style="color:green"></div>
          <div v-else class="fa fa-comment-slash" style="color:red"></div>
        </template>
        <template v-slot:cell(details)="row">
            <button class="btn btn-secondary ml-auto" role="button" v-b-modal.mealEditorModal @click="editorMode='Edit'; editRow=row">
              <div class="fa fa-edit"></div>
            </button>
            <button class="btn btn-danger ml-auto" role="button" v-on:click="remove(row)">
              <div class="fa fa-trash-alt"></div>
            </button>
        </template>
      </b-table>
    </div>
  <b-modal id="mealEditorModal" :title="editorMode+' Meal'"
      @show="loadModal"
      @hidden="resetModal"
      @ok="handleOk"
  >
    <form ref="mealEditorForm" @submit.stop.prevent="handleSubmit">
      <div class="alert alert-danger" v-if="errorString">{{errorString}}</div>
        <b-form-group
          :state="mealEditorState.name"
          label="Name"
          label-for="name-input"
          invalid-feedback="Name is required"
        >
          <b-form-input
            id="name-input"
            v-model="mealEditor.name"
            :state="mealEditorState.name"
            required
          ></b-form-input>
        </b-form-group>
        <b-form-group
          :state="mealEditorState.time"
          label="Time"
          label-for="time-input"
          invalid-feedback="Time is required"
        >
          <b-time
            id="time-input"
            v-model="mealEditor.time"
            :state="mealEditorState.time"
            required
          ></b-time>
        </b-form-group>
        <b-form-group
          :state="mealEditorState.servings"
          label="Servings"
          label-for="servings-input"
          invalid-feedback="Servings are required"
        >
          <b-form-input
            id="servings-input"
            v-model="mealEditor.servings"
            :state="mealEditorState.servings"
            type="number"
            required
          ></b-form-input>
        </b-form-group>
        <b-form-group
          :state="mealEditorState.notify"
          label="Notify on Telegram"
          label-for="notify-checkbox"
          invalid-feedback="notify is required"
        >
          <b-form-checkbox
            id="notify-checkbox"
            v-model="mealEditor.notify"
            :state="mealEditorState.notify"
            type="checkbox"
            required
          ></b-form-checkbox>
        </b-form-group>
    </form>
  </b-modal>
  </b-container-fluid>
</template>
`
})
